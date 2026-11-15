# Knowledge changelog

## Unreleased

### Changed

- `GET /v1/search` is now semantic: local CPU embeddings (fastembed/ONNX,
  default `intfloat/multilingual-e5-small`, 384 dims, English/Hindi/Tamil) stored in
  pgvector with an HNSW cosine index; hybrid re-rank adds a keyword bonus for literal
  matches. Tenant scope and role checks unchanged. Response shape unchanged; hits gain
  optional `score`, request gains optional `limit` (1-50, default 10).
- Postgres path requires pgvector >= 0.8 and a loadable embedder and fails closed
  otherwise; no substring fallback. Fixture memory mode keeps substring search.
- Articles are embedded on every upsert (create/update/seed); `serve` embeds stale rows
  at startup.
- Postgres integration tests use pinned `pgvector/pgvector:pg17`, honour
  `KNOWLEDGE_TEST_DATABASE_URL`, and skip without Docker.

- Default preview listen moved to `127.0.0.1:8035` (8034 = merchant-teams;
  8028 stays merchant-inbox).

### Added

- `EmbedderPort` (`application.ports.Embedder`) with `FastEmbedEmbedder` adapter;
  env `KNOWLEDGE_EMBEDDING_MODEL`, `KNOWLEDGE_EMBEDDING_CACHE_DIR`.
- `sentinel-knowledge reindex [--all]` / `make reindex`: migrate pgvector schema and
  backfill embeddings (recreates the column on model dimension change).
- `/v1/capabilities` reports `search` (`semantic-hybrid` or `substring`).
- Test-only deterministic `FakeEmbedder`; ranking test ("charged twice" finds the
  duplicate-payment article that substring search misses); opt-in real-model tests
  (`KNOWLEDGE_TEST_REAL_EMBEDDER=1`) incl. Hindi and Tamil queries; fail-closed tests
  for unknown model, missing pgvector and dimension mismatch.

- Independent `knowledge.v1` HTTP service: article list, detail, and ILIKE search.
- Fixture memory store and optional PostgreSQL adapter (`KNOWLEDGE_DATABASE_URL`).
- `make seed` / `sentinel-knowledge seed` writes synthetic `article-demo-refund-policy`
  for `tenant-demo` (idempotent Postgres upsert; evidence label synthetic-sandbox).
- Module `make check`, `.env.example`, contract snapshot, compatibility checklist.
- Default preview listen `127.0.0.1:8035`.
- Contract pin: `sentinel.task-contracts.v1` SHA-256
  `0db3ba2bba994f10d3060bc7173035360c15ffe23189cea409f7327e23c36feb`.
- Capabilities advertise `financial_authority=false`; no ledger surfaces.
