# SN-013 changelog

## Unreleased

### Added — 13 November 2026

- Independent module ownership, architecture/interface guide, scoped agent rules and acceptance checklist.
- `approval-ui.v1` embeddable `ApprovalPanel`, view-model validation, injected `decide` client, refresh/conflict events.
- Standalone Vite preview, fixtures, contract snapshots, and `case-api.v1` / `action-ledger.v1` stubs (valid, unavailable, malformed, unauthorized_or_out_of_scope, plus expired/stale/cross-tenant/409).
- Real-peer HTTP adapters for case-api and action-ledger decision routes without fixture fallback.
- `make setup`, `make check`, and `make preview` with npm lockfile.

### Implementation status

- Module-local `make check` is the component deliverable.
- Real assembled peers remain unverified; fixture success is not release evidence.
