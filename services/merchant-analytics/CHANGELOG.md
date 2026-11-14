# SN-032 changelog

## Unreleased
- Postgres metrics snapshots via `MERCHANT_ANALYTICS_DATABASE_URL`; real-peers with
  DB serves `GET /v1/merchants/{merchant_ref}/metrics` from
  `merchant_analytics.merchant_metrics_snapshots` (404 `SNAPSHOT_NOT_FOUND` when
  missing; 503 when DB down). `make seed` writes one `merchant-demo-1` row.
- Refuse non-loopback HTTP bind while demo/sandbox bearer tokens remain configured.

### Fixed

- `case_http` aligns to case-api.v1 Case fields; missing analytics-required
  `opened_at`/`intent`/`evidence_ids` fail closed (no invented UNKNOWN/timestamps).

### Added

- Independent `merchant-analytics.v1` HTTP service with read-only
  `GET /v1/merchants/{merchant_ref}/metrics`.
- Domain aggregates: exception rate, unresolved minor units, refund aging buckets,
  median handling seconds, top causes.
- Fixture and real-peer adapters for `case-api.v1` / `evidence.v1`; stubs for
  valid, unavailable, malformed, unauthorized_or_out_of_scope.
- Contract pin: `sentinel.task-contracts.v1` SHA-256
  `0db3ba2bba994f10d3060bc7173035360c15ffe23189cea409f7327e23c36feb`.
- Module `make check` (ruff + pytest) and standalone README.
