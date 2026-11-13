# SN-011 changelog

## Unreleased

### Added — 13 November 2026

- `sentinel-verifier` implementing `verifier.v1`: signed webhook inbox, scheduled rechecks, closure assessments.
- Local `payment-provider.v1`, `action-ledger.v1`, `evidence.v1`, and `case-api.v1` stubs under `tests/stubs/`.
- HTTP real-peer adapters for all consumed ports (no fixture fallback).
- Module `make check` (ruff + pytest with private PostgreSQL for durable inbox).
- Contract snapshots, demo fixtures, migration SQL, and real-peer compatibility checklist.

### Validation observed

- Contract baseline SHA-256 `0c728513e8b4ec0f34bcef63faa0207160d45cc7f20f872c1d9136ca7e252ffa`.
- Commands: `make -C services/verifier check` (see PR evidence).
- Fixture modes only for peers; durable inbox uses real PostgreSQL in a disposable container.
- Assembly against real SN-004/SN-005/SN-008/SN-009 peers: unverified.
