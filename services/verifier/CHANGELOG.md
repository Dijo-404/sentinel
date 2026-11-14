# SN-011 changelog

## Unreleased

### Changed — 14 November 2026

- Demo tenant default `tenant-demo`; accepts canonical `tok-*` bearers with legacy aliases. Refs #77.

### Fixed — 14 November 2026

- Unprocessed inbox duplicates re-run provider reconciliation after crash-after-insert.
- Real-peers bootstrap refuses demo webhook HMAC and demo peer bearer defaults.
- PENDING refund synthetic evidence uses `verification_status=UNVERIFIED`.
- `drain_due_rechecks` / `POST /v1/rechecks/drain` / CLI claim due SCHEDULED or lease-expired jobs.
- Empty `case_ids` deny; `"*"` allows; demo principals use `"*"`.

### Added — 13 November 2026

- `sentinel-verifier` implementing `verifier.v1`: signed webhook inbox, scheduled rechecks, closure assessments.
- Local `payment-provider.v1`, `action-ledger.v1`, `evidence.v1`, and `case-api.v1` stubs under `tests/stubs/`.
- HTTP real-peer adapters for all consumed ports (no fixture fallback).
- Module `make check` (ruff + pytest with private PostgreSQL for durable inbox).
- Contract snapshots, demo fixtures, migration SQL, and real-peer compatibility checklist.

### Validation observed

- Contract baseline SHA-256 `0db3ba2bba994f10d3060bc7173035360c15ffe23189cea409f7327e23c36feb`.
- Commands: `make -C services/verifier check` (see PR evidence).
- Fixture modes only for peers; durable inbox uses real PostgreSQL in a disposable container.
- Assembly against real SN-004/SN-005/SN-008/SN-009 peers: unverified.
