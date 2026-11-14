# SN-030 changelog

## Unreleased

### Added

- PostgreSQL adapter (`DISPUTES_DATABASE_URL=postgresql+psycopg://...`), schema
  `merchant_disputes`, `make migrate`, and sandbox `make seed` (one `OPEN`
  dispute for `tenant-demo` only).
- `GET /v1/merchants/{merchant_ref}/disputes` list route; detail remains
  `GET /v1/disputes/{dispute_id}`.
- Disposable Docker Postgres persistence tests for list/get + seed gates.

### Fixed

- Real-peers bootstrap refuses default `MemoryDisputeStore`; requires
  `DISPUTES_DATABASE_URL` (Postgres or sqlite) or an injected durable store so
  worker processes cannot wipe or split state.

- Refuse non-loopback HTTP bind while demo/sandbox bearer tokens remain configured.

### Added (baseline)

- Independent `merchant-disputes.v1` HTTP service with dispute lifecycle, evidence packet assembly, and deadline tracking.
- Fixture and real-peer adapters for `case-api.v1` and `evidence.v1`; local stubs for valid/unavailable/malformed/unauthorized cases.
- Acceptance tests for lifecycle, evidence gate, deadline overdue, and fail-closed peer/auth behavior.
- Module `make check`, `.env.example`, contract snapshot, and compatibility checklist.
- Contract pin: `sentinel.task-contracts.v1` SHA-256 `0db3ba2bba994f10d3060bc7173035360c15ffe23189cea409f7327e23c36feb`.
