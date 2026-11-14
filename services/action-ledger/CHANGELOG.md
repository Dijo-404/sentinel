# SN-009 changelog

## Unreleased

### Added — SN-040 peer principal catalog

- Additive `merchant` / `risk_officer` / `platform_admin` demo tokens and
  `contracts/principals.json` catalog. Decide still requires exact `supervisor`.
  Refs #103.
- `contracts/COMPATIBILITY.md`; unit tests that extended humans fail `_require_roles(..., "supervisor")`.

- Refuse non-loopback HTTP bind while demo/sandbox bearer tokens remain configured.

### Changed — 14 November 2026

- Demo tenant default `tenant-demo`; accepts canonical `tok-*` bearers with legacy `token-*-demo` aliases. Refs #77.

### Fixed — 14 November 2026

- Unify claim/outcome lock order: always lock `actions` before updating `outbox` (avoids AB-BA deadlock).
- `ReservationNetworkGuard` state is contextvars-scoped so FastAPI threadpool requests do not race a process singleton.
- Eligibility supersession check requires `locked_elig.version == next_version` (ON CONFLICT bumps version).
- `write_payment_balance` raises `ConflictError` (`PAYMENT_BALANCE_CONFLICT`) when rowcount != 1.
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
- Contract snapshots and canonical digest vector pinned to baseline SHA-256 `0db3ba2bba994f10d3060bc7173035360c15ffe23189cea409f7327e23c36feb`.

### Implementation status

- Standalone module checks are the deliverable. Real assembled policy/evidence peers remain **UNVERIFIED**.
- Payment provider writes stay out of this service (dispatcher owns them).
