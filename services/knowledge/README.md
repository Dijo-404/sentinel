# Knowledge service (knowledge.v1)

Standalone articles and search peer for the operator knowledge base. Read-only HTTP
surface; no money authority.

**Owned root:** `services/knowledge/` · **Branch:** `feat/portal-wave4-intel-voice-approval`

Contract: `sentinel.task-contracts.v1`, SHA-256
`0db3ba2bba994f10d3060bc7173035360c15ffe23189cea409f7327e23c36feb`.

## Standalone setup and checks

```sh
make -C services/knowledge check
```

Installs only this module's `uv` dependencies (`pyproject.toml` / `uv.lock`). No sibling
Sentinel services required. PostgreSQL with the `pgvector` extension via
`KNOWLEDGE_DATABASE_URL` (required for `make seed` and real-peers durable state).

`make check` runs unit tests with a deterministic test-only embedder and, when Docker is
available, starts private `pgvector/pgvector:pg17` and plain `postgres:17-alpine`
containers for the integration tests (skipped without Docker). Point
`KNOWLEDGE_TEST_DATABASE_URL` at an existing pgvector database to skip the container.
To also download and exercise the real ONNX model (English/Hindi/Tamil ranking and
the Postgres tests with real 384-dim vectors):

```sh
cd services/knowledge
KNOWLEDGE_TEST_REAL_EMBEDDER=1 uv run --frozen pytest
```

Preview (fixture mode, port **8035**):

```sh
cp services/knowledge/.env.example services/knowledge/.env
make -C services/knowledge preview
```

Sandbox seed (writes ≥1 article for `tenant-demo`):

```sh
# KNOWLEDGE_DATABASE_URL must point at Postgres
make -C services/knowledge seed
```

Stable seed id: `article-demo-refund-policy`. Evidence label: synthetic-sandbox.
Idempotent upsert. Seed refuses non-`tenant-demo` rows. Seeded rows are embedded on
write, so seeding needs the embedding model (downloaded on first use) and pgvector.

## Semantic search

`GET /v1/search` ranks articles by meaning, not substring. Postgres path:

1. Each article's `title + summary + body` is embedded locally on CPU on every
   upsert (create/update) with [fastembed](https://github.com/qdrant/fastembed)
   (ONNX Runtime). No external embedding API is called.
2. Vectors live in `knowledge.articles.embedding vector(384)` with an HNSW index
   (`vector_cosine_ops`); `embedding_model` records which model produced each vector.
3. Search embeds the query, takes the cosine top candidates (tenant-filtered, with
   `hnsw.iterative_scan = relaxed_order` so filtering never starves results) unioned
   with literal keyword matches, and re-ranks by
   `cosine_similarity + 0.05 if the query appears verbatim in title/summary/body`.
4. Tenant scope and operator/supervisor authorization are unchanged.

Default model: **`intfloat/multilingual-e5-small`** (MIT, 384 dims, XLM-R tokenizer,
~100 languages incl. Hindi and Tamil). fastembed's built-in multilingual options were
either missing Tamil from training (`paraphrase-multilingual-MiniLM-L12-v2`, 50 langs) or
much heavier (`multilingual-e5-large`, 2.2 GB). e5-small is not in fastembed's catalog,
so the adapter registers its upstream ONNX export (`onnx/model.onnx`) as a custom
mean-pooled, normalized model and applies the `query: ` / `passage: ` prefixes E5 expects.
Any fastembed catalog model (e.g. `BAAI/bge-small-en-v1.5`) can be set instead.

Footprint (measured, x86-64, 22 cores): model cache ~465 MB on disk (470 MB fp32 ONNX +
17 MB tokenizer); ~0.9 GB peak RSS for a process that loads it; ~1 s load from cache;
~10 ms per short query embedding. Inputs beyond 512 tokens are truncated (no chunking).

Fail closed: if the model cannot load/download, the `vector` extension is missing or
older than 0.8, or the stored vector dimension differs from the model, startup, seed
and reindex raise `PEER_UNAVAILABLE` / `CONFIGURATION`. There is no substring fallback on
the Postgres path. Fixture mode without a database keeps the in-memory substring search
and labels it `search: "substring"` in `/v1/capabilities` (`semantic-hybrid` otherwise).

### Deploy (Postgres = `pgvector/pgvector:pg17`)

| Env                             | Required | Meaning                                                    |
| ------------------------------- | -------- | ---------------------------------------------------------- |
| `KNOWLEDGE_DATABASE_URL`        | yes      | `postgresql+psycopg://...` on a pgvector-enabled server    |
| `KNOWLEDGE_MODE`                | yes      | `real-peers` in deploys                                    |
| `KNOWLEDGE_EMBEDDING_MODEL`     | no       | default `intfloat/multilingual-e5-small`                   |
| `KNOWLEDGE_EMBEDDING_CACHE_DIR` | advised  | persistent dir for model files (fastembed default is /tmp) |
| `HF_HUB_OFFLINE`                | no       | `1` to forbid network once the cache is populated          |

The database role must be allowed to `CREATE EXTENSION vector` once (superuser in the
stock image), or a DBA runs `CREATE EXTENSION IF NOT EXISTS vector;` beforehand.

```sh
# one-off after deploy / after changing KNOWLEDGE_EMBEDDING_MODEL:
# migrate (extension, column, HNSW index) and embed every row lacking a current vector
make -C services/knowledge reindex          # or: sentinel-knowledge reindex [--all]
make -C services/knowledge seed             # sandbox article, embedded on write
```

`serve` also migrates and embeds stale rows at startup, so `reindex` is a safety net and
the required step when the model (and therefore the vector dimension) changes: only
`reindex` drops and recreates a mismatched `embedding` column; `serve` refuses to start.
Pre-download the model into the cache dir at image build time by running `reindex`
(or any start) once, then set `HF_HUB_OFFLINE=1`.

## Scope

- Owns knowledge articles and their semantic (pgvector) search only.
- Bearer principal + tenant scope; operator/supervisor roles only.
- Does **not** call ledger decide, mint refunds, or edit SN-009 tables.
- `financial_authority` capability is always `false`.

## Routes

| Method | Path                   | Auth                 | Notes                                    |
| ------ | ---------------------- | -------------------- | ---------------------------------------- |
| GET    | `/healthz`             | none                 | liveness                                 |
| GET    | `/readyz`              | none                 | labels `mode`                            |
| GET    | `/v1/capabilities`     | none                 | `financial_authority=false`, `search`    |
| GET    | `/v1/articles`         | operator, supervisor | list summaries                           |
| GET    | `/v1/articles/{id}`    | operator, supervisor | full body                                |
| GET    | `/v1/search?q=&limit=` | operator, supervisor | semantic top-k; `limit` 1-50, default 10 |

Search response stays `{ "hits": ArticleSummary[] }`, best first. Each hit gains an
optional `score` (cosine similarity + keyword bonus, roughly 0-1.05; omitted on the
fixture substring path). Results are always top-k, so RAG callers should apply their own
`score` threshold if they need one.

## Real-peer mode

Set `KNOWLEDGE_MODE=real-peers` plus `KNOWLEDGE_DATABASE_URL` (or inject a durable
store). Missing durable store, pgvector or embedder fails closed; fixture memory and
substring search are never substituted.

## Untested assembly boundaries

Portal BFF proxy and operator Knowledge page wiring are Wave 4 follow-on tasks.
Live multi-service assembly is unverified until owner-run. The assembly seed
(`integration/core` runs `make seed`) now needs a pgvector-enabled database and the model
cache. Long articles are embedded as one truncated passage (no chunking yet).
