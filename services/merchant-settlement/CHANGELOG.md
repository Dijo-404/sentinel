# SN-027 changelog

## Unreleased

### Added — 13 November 2026

- Independent `sentinel-merchant-settlement` package: domain reconciliation, import/assign/close use cases, FastAPI `merchant-settlement.v1` routes.
- Local `evidence.v1` and `payment-provider.v1` stubs under `tests/stubs/` (valid, unavailable, malformed, unauthorized_or_out_of_scope).
- Real-peer HTTP adapters that fail closed (no fixture fallback).
- Module `Makefile` (`setup`/`check`/`preview`), `uv.lock`, `.env.example`, contract snapshots, JSON/CSV fixtures, acceptance tests.
- Contract pin: `sentinel.task-contracts.v1` SHA-256 `0db3ba2bba994f10d3060bc7173035360c15ffe23189cea409f7327e23c36feb`.

### Verification (observed)

- `make -C services/merchant-settlement check` → ruff clean; pytest `20 passed` (fixture mode labeled).
- Root `make check` from worktree → repository metadata checks passed.
- Contract baseline SHA-256 `0db3ba2bba994f10d3060bc7173035360c15ffe23189cea409f7327e23c36feb`.
- Local stubs only (`tests/stubs/`); no sibling Sentinel service or real payment credentials.

### Implementation status

- Standalone `make -C services/merchant-settlement check` is implemented and required for review.
- Real-peer integration against assembled SN-004/SN-006 remains unverified; fixture peers are not release evidence.
