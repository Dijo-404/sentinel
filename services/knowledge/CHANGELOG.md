# Knowledge changelog

## Unreleased

### Changed

- Default preview listen moved to `127.0.0.1:8034` (8028 stays merchant-inbox).

### Added

- Independent `knowledge.v1` HTTP service: article list, detail, and ILIKE search.
- Fixture memory store and optional PostgreSQL adapter (`KNOWLEDGE_DATABASE_URL`).
- `make seed` / `sentinel-knowledge seed` writes synthetic `article-demo-refund-policy`
  for `tenant-demo` (idempotent Postgres upsert; evidence label synthetic-sandbox).
- Module `make check`, `.env.example`, contract snapshot, compatibility checklist.
- Default preview listen `127.0.0.1:8034`.
- Contract pin: `sentinel.task-contracts.v1` SHA-256
  `0db3ba2bba994f10d3060bc7173035360c15ffe23189cea409f7327e23c36feb`.
- Capabilities advertise `financial_authority=false`; no ledger surfaces.
