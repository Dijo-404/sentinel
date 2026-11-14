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
Sentinel services required. PostgreSQL via `KNOWLEDGE_DATABASE_URL` (required for
`make seed` and real-peers durable state).

Preview (fixture mode, port **8034**):

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
Idempotent upsert. Seed refuses non-`tenant-demo` rows.

## Scope

- Owns knowledge articles and title/summary/body ILIKE search only.
- Bearer principal + tenant scope; operator/supervisor roles only.
- Does **not** call ledger decide, mint refunds, or edit SN-009 tables.
- `financial_authority` capability is always `false`.

## Routes

| Method | Path | Auth | Notes |
| --- | --- | --- | --- |
| GET | `/healthz` | none | liveness |
| GET | `/readyz` | none | labels `mode` |
| GET | `/v1/capabilities` | none | `financial_authority=false` |
| GET | `/v1/articles` | operator, supervisor | list summaries |
| GET | `/v1/articles/{id}` | operator, supervisor | full body |
| GET | `/v1/search?q=` | operator, supervisor | ILIKE match |

## Real-peer mode

Set `KNOWLEDGE_MODE=real-peers` plus `KNOWLEDGE_DATABASE_URL` (or inject a durable
store). Missing durable store fails closed; fixture memory is never substituted.

## Untested assembly boundaries

Portal BFF proxy and operator Knowledge page wiring are Wave 4 follow-on tasks.
Live multi-service assembly is unverified until owner-run.
