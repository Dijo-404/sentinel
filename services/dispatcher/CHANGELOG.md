# SN-010 changelog

## Unreleased

### Fixed

- Timeout and non-auth peer errors keep the job in `SUBMITTED` (list_incomplete) until lookup / same-key retry finishes; only then set `OUTCOME_REPORTED` or `ESCALATED`.

### Added — 13 November 2026

- `sentinel-dispatcher` worker implementing `dispatcher.v1`: claim → provider dispatch → ledger outcome, with durable PostgreSQL checkpoints and crash recovery.
- Local `action-ledger.v1` and `payment-provider.v1` stubs under `tests/stubs/` including commit-then-timeout and ambiguous lookup faults.
- HTTP real-peer adapters for ledger/provider ports (no fixture fallback).
- Module `make check` (ruff + pytest with private PostgreSQL).
- Contract snapshots, demo fixtures, migration SQL, and real-peer compatibility checklist.

### Validation observed

- Contract baseline SHA-256 `0c728513e8b4ec0f34bcef63faa0207160d45cc7f20f872c1d9136ca7e252ffa`.
- Commands: `make -C services/dispatcher check` (see PR evidence).
- Fixture modes only for peers; durable recovery uses real PostgreSQL in a disposable container.
- Assembly against real SN-009/SN-004 peers: unverified.
