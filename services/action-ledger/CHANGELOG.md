# SN-009 changelog

## Unreleased

### Added — 13 November 2026

- `sentinel-action-ledger` service implementing `action-ledger.v1`: proposals, decisions, reservations, claims, get, outcomes.
- PostgreSQL schema/migrations for actions, approvals, payment_reservations, eligibility_snapshots, outbox, financial_audit, outcome_events.
- Local `policy.v1` / `evidence.v1` stubs and fail-closed HTTP real-peer adapters.
- Real Postgres concurrency and atomicity proofs; `make check` via uv/ruff/pytest.
- Contract snapshots and canonical digest vector pinned to baseline SHA-256 `0c728513e8b4ec0f34bcef63faa0207160d45cc7f20f872c1d9136ca7e252ffa`.

### Implementation status

- Standalone module checks are the deliverable. Real assembled policy/evidence peers remain **UNVERIFIED**.
- Payment provider writes stay out of this service (dispatcher owns them).
