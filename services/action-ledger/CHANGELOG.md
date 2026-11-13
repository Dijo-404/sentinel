# SN-009 changelog

## Unreleased

### Fixed — 14 November 2026

- Enforce subject_ref scope on eligibility (empty subject_refs still allowed for service principals).
- Mark outbox DONE on post-claim outcomes; claim skips DISPATCHING rewrite when action already progressed.
- Bind PROVIDER/FAILED/CREDIT outcome evidence fields to the action; reject mismatches.
- Monotonic eligibility snapshot versions under lock; unique lease_id per claimed outbox row.
- Principal.allows_case denies empty case_ids; wildcard `"*"` grants broad case access.

### Added — 13 November 2026

- `sentinel-action-ledger` service implementing `action-ledger.v1`: proposals, decisions, reservations, claims, get, outcomes.
- PostgreSQL schema/migrations for actions, approvals, payment_reservations, eligibility_snapshots, outbox, financial_audit, outcome_events.
- Local `policy.v1` / `evidence.v1` stubs and fail-closed HTTP real-peer adapters.
- Real Postgres concurrency and atomicity proofs; `make check` via uv/ruff/pytest.
- Contract snapshots and canonical digest vector pinned to baseline SHA-256 `0c728513e8b4ec0f34bcef63faa0207160d45cc7f20f872c1d9136ca7e252ffa`.

### Implementation status

- Standalone module checks are the deliverable. Real assembled policy/evidence peers remain **UNVERIFIED**.
- Payment provider writes stay out of this service (dispatcher owns them).
