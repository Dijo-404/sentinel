# SN-006 changelog

## Unreleased
- Refuse non-loopback HTTP bind while demo/sandbox bearer tokens remain configured.

### Fixed — cross-service order identity

- Collect maps authorized case `order_reference` (`{subject_ref}/{customer_order_id}` or
  `:` boundary) to the bare provider/simulator order key before payment-provider reads.
  Authorized reference on the collect request/store row is unchanged. Malformed boundaries
  fail closed. Fixture scenario markers moved to `#` so they do not collide with subject
  boundaries.

### Changed — 14 November 2026

- `.env.example` / test token map accept canonical `tok-workflow` / `tok-verifier` (legacy aliases kept). Refs #77.

### Fixed

- Require `DATABASE_URL` unless `SENTINEL_EVIDENCE_ALLOW_MEMORY=1`, `EVIDENCE_MODE=fixture`, or pytest; no silent memory fallback for real-peers.
- Empty `case_ids` deny; `*` allows all cases (deny-by-default).

### Added — 13 November 2026

- Independent module ownership, architecture/interface guide, scoped agent rules and acceptance checklist.
- `sentinel-evidence` package: domain reconciliation, collect/list use cases, FastAPI `evidence.v1` routes.
- Local `payment-provider.v1` stubs under `tests/stubs/` (valid, unavailable, malformed, unauthorized_or_out_of_scope) plus stale/conflict/equal-amount fixtures.
- Real-peer HTTP provider adapter that fails closed (no fixture fallback).
- PostgreSQL evidence storage (schema/tables via `sentinel-evidence migrate`) retaining original payload bytes and digests.
- Module `Makefile` (`setup`/`check`/`preview`), lockfile, `.env.example`, contract snapshot, acceptance tests.

### Implementation status

- Standalone `make -C services/evidence check` is implemented and required for review.
- Real-peer integration against an assembled SN-004 simulator remains unverified; fixture peers are not release evidence.
