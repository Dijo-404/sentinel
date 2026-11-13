# SN-020 changelog

## Unreleased

### Added — 13 November 2026

- `finharness-sdk.v1` Python package: injectable evidence/policy/ledger/verifier/indic-context ports, version-pinned `CaseManifest`, `RuntimeConfig` with disabled-by-default routing/writes/notifications, and `FinHarnessClient` composition facade.
- Local sample workflow (`run_sample_workflow` / `sentinel-finharness sample`) exercising fixture peers with contract validation.
- Peer stubs under `tests/stubs/` covering valid, unavailable, malformed, and unauthorized_or_out_of_scope for all five consumed ports.
- Module Makefile `setup`/`check`/`preview`, lockfile, `.env.example`, and contract snapshot `contracts/finharness-sdk.v1.json`.

### Implementation status

- Standalone fixture checks only. Real-peer adapters, payment simulator runs, live model calls, and assembled product evidence remain unverified.
- No independent refund executor or case store; SN-009 remains sole financial authority.
