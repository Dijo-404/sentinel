# SN-009 changelog

## Unreleased

### Fixed — approved reservation policy recheck (Refs #144)

- Forward the stored supervisor approval when rechecking policy before reservation.
  The reservation transaction still validates approval binding, digest, revision,
  policy version and expiry before creating financial state.

### Added — portal session authentication

- Optional `LEDGER_IDENTITY_BASE_URL`: bearers not in the static token map are resolved via
  identity `GET /v1/auth/me`. Identity `supervisor` → ledger `supervisor`, `operator` → read-only
  `operator`; all other roles 403. `principal_id` is the identity `user_id`, so approvals record
  the exact human reviewer. Identity unavailable/5xx → 503, malformed/non-200 → 401, inactive
  user or missing/revoked assignment → 403. Unset = unchanged static-token behaviour. Refs #144.
- Session principals get tenant-wide scope only for `scope_key == "tenant:<tenant_id>"` with null
  `merchant_ref` / `team_id`; merchant/team-scoped, missing, malformed or mismatched-tenant
  scopes → 403 (security review on #152).

### Fixed — payment merchant_ref provenance

- Reservation `payment_reservations.merchant_ref` comes from verified payment
  evidence `payment.merchant_ref`. Refuses missing values and rejects
  `merchant_ref == case_id` (no more case-id substitution).

### Added — SN-040 peer principal catalog

- Additive `merchant` / `risk_officer` / `platform_admin` demo tokens and
  `contracts/principals.json` catalog. Decide still requires exact `supervisor`.
  Refs #103.
- `contracts/COMPATIBILITY.md`; unit tests that extended humans fail `_require_roles(..., "supervisor")`.

- Refuse non-loopback HTTP bind while demo/sandbox bearer tokens remain configured.

### Changed — 14 November 2026

- Demo tenant default `tenant-demo`; accepts canonical `tok-*` bearers with legacy `token-*-demo` aliases. Refs #77.

### Fixed — 14 November 2026

- `reserve()` enforces policy.v1 `ALLOW` plus matching `action_digest` /
  `policy_version` before the reservation TX; DENY/non-ALLOW raises
  `POLICY_DENIED`. Require explicit `order_reference` (or proposal payload
  identity); stop inventing `ORDER-{transaction_ref}`.
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
