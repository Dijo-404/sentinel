# assistant.v1 changelog

## Unreleased

### Added

- Independent `assistant.v1` HTTP service: threads and sandbox-labeled messages.
- Routes: `GET /v1/health`, `GET /v1/capabilities`, thread list/create, message list/post.
- Fixture memory store and optional PostgreSQL adapter (`ASSISTANT_DATABASE_URL`).
- `make seed` upserts synthetic thread + messages for `tenant-demo` (`evidence_mode=sandbox`).
- Module `make check`, `.env.example`, contract snapshot, migrations README.
- Default preview listen `127.0.0.1:8026`.
- Stub assistant reply on message post; `financial_authority=false`; no ledger writes.
