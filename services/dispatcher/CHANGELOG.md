# SN-010 changelog

## Unreleased

### Added — 14 November 2026

- Minimal FastAPI probe surface: `GET /healthz`, `GET /readyz`, `GET /v1/capabilities` (`contract_version=sentinel.task-contracts.v1`, `component=dispatcher`, `port=dispatcher.v1`, `mode` from `DISPATCHER_MODE`).
- `make preview` starts uvicorn on `127.0.0.1:8010`. Worker path remains CLI `run-once` / `recover`.
- Docs: payment-provider peer is the mock sandbox simulator; a future Paytm adapter must keep `payment-provider.v1` without changing dispatcher financial rules.

### Changed — 14 November 2026

- Sandbox tenant default `tenant-demo`; bearer `tok-dispatcher`. Refs #77.

### Fixed

- Timeout and non-auth peer errors keep the job in `SUBMITTED` (list_incomplete) until lookup / same-key retry finishes; only then set `OUTCOME_REPORTED` or `ESCALATED`.
- Provider `FAILED_FINAL` maps to ledger `ESCALATED` (reservation retained); dispatcher never reports `FAILED_FINAL`.
- Stub ledger rejects illegal dispatcher `FAILED_FINAL` and never discards reservations on that path.
- `LEASE_MISMATCH` from `report_outcome` marks the job `SUPERSEDED` so it leaves `list_incomplete`.
- Refund evidence `observed_at` / `expires_at` come from the worker clock.

### Added — 13 November 2026

- `sentinel-dispatcher` worker implementing `dispatcher.v1`: claim → provider dispatch → ledger outcome, with durable PostgreSQL checkpoints and crash recovery.
- Local `action-ledger.v1` and `payment-provider.v1` stubs under `tests/stubs/` including commit-then-timeout and ambiguous lookup faults.
- HTTP real-peer adapters for ledger/provider ports (no fixture fallback).
- Module `make check` (ruff + pytest with private PostgreSQL).
- Contract snapshots, demo fixtures, migration SQL, and real-peer compatibility checklist.

### Validation observed

- Contract baseline SHA-256 `0db3ba2bba994f10d3060bc7173035360c15ffe23189cea409f7327e23c36feb`.
- Commands: `make -C services/dispatcher check` (see PR evidence).
- Fixture modes only for peers; durable recovery uses real PostgreSQL in a disposable container.
- Assembly against real SN-009/SN-004 peers: unverified.
