# SN-007 changelog

## Unreleased

### Fixed — 15 November 2026 (ops projection isolation + HISTORY coverage)

- HISTORY tests cover both `VERIFIED_RESOLVED` and `CLOSED_NO_ACTION`; cross-tenant ops isolation for messages/audit/HISTORY.
- README: audit feed returns stored payloads (writers already sanitize; no separate read redaction).

### Added — 15 November 2026 (ops messages / history / audit projections)

- `GET /v1/ops/messages` tenant-scoped newest-first message inbox (operator/supervisor; max 50).
- `GET /v1/ops/audit-events` tenant-scoped newest-first case event feed (operator/supervisor; max 50).
- `GET /v1/ops/cases?status=HISTORY` expands to `{VERIFIED_RESOLVED, CLOSED_NO_ACTION}`; comma-separated status filters also accepted.

### Fixed — 15 November 2026 (supervisor dashboard pending_approvals)

- `pending_approvals` is the case-store count of `WAITING_APPROVAL` rows (same as
  `waiting_approval_cases`), not a literal `0`.

### Fixed — order reference identity + workflow outbox crash recovery

- Canonical authorized `order_reference` remains `{subject_ref}/{customer_order_id}`
  (e.g. `subject-a/DEMO-ORDER-42`). Intake value is preserved through CaseInput and
  workflow outbox scheduling payloads; HTTP `POST /v1/runs` still uses the wire subset
  (order identity loaded from CaseInput). Bare provider ids stay unbound.
- Case create inserts the START outbox row in the same transaction as the case.
- Workflow outbox claims set `lease_expires_at`; stale `CLAIMED` jobs (expired or null
  lease) are reclaimable. Continuous delivery: `make -C apps/api flush-workflow` or
  `sentinel-api flush-workflow --loop` (mutation-time flush remains as a best-effort hook).

### Fixed — real-peers identity session projection

- `real-peers` + `IDENTITY_BASE_URL` / `SENTINEL_API_IDENTITY_BASE_URL`: resolve human
  bearers via identity `GET /v1/auth/me`, mapping `active_assignment` → `Principal`.
  Opaque TokenMap remains for service tokens (`tok-*`). Fail closed on unavailable /
  malformed identity responses. Bind safety refuses non-loopback while identity
  session projection is enabled.

### Added — SN-040 peer principal catalog

- Fixture principals for `merchant` / `risk_officer` / `platform_admin` (opaque
  tokens + identity sessions). Decide path still supervisor-only; extended
  humans → 403 with ledger untouched. Refs #103.
- `contracts/COMPATIBILITY.md` money-authority checklist.

### Fixed — 14 November 2026 (SN-037 review)

- Fixture identity sessions wire only in `fixture` mode; `real-peers` uses opaque token map (future BFF). Refs #101.
- Bind safety treats `sess-*` fixture session credentials as demo offenders. Refs #101.
- `apply_result` preserves `assigned_principal_id` through updates and idempotent replay. Refs #101.

### Added — 14 November 2026 (SN-037)

- Identity principal adapter port with fixture session/BFF projection double (`fixtures/identity_sessions.json`); composite resolver prefers identity projection then opaque token map for service peers. Refs #101.
- `POST /v1/ops/cases/{caseId}/claim` atomic assignment (`assigned_principal_id`); conflict → `ASSIGNMENT_CONFLICT` 409. Refs #101.
- Portal aggregate/list projections: `GET /v1/customer/dashboard`, `GET /v1/customer/cases`, `GET /v1/operator/dashboard`, `GET /v1/supervisor/dashboard` (supervisor pending approvals remain ledger-owned stub). Refs #101.
- AUTH-06/AUTH-08 + claim concurrency coverage; subject_refs binding on create unchanged. Refs #101.

### Unreleased (prior)
- Refuse non-loopback HTTP bind while demo/sandbox bearer tokens remain configured.

### Changed — 14 November 2026

- Fixture token map accepts canonical sandbox bearers (`tok-workflow`, `tok-case-api`, `tok-customer`, …) alongside legacy aliases; points at `integration/core` matrix. Refs #77.

### Fixed

- Case create requires `order_reference` bound to principal `subject_refs` for customers (and any principal with non-empty `subject_refs`); fail closed. Prevents opening a case on another subject's order while stamping the caller's `subject_ref`.
- Decide path calls `require_case_access` after resolving `case_id` from the action index.
- Atomic workflow outbox claim (`PENDING` → `CLAIMED` via `FOR UPDATE SKIP LOCKED`).
- Decide path binds action to case before calling ledger; unknown action returns 404.
- Workflow/verifier empty `case_ids` deny by default; fixtures use `"*"` wildcard.

### Added — 13 November 2026

- Independent module ownership, architecture/interface guide, scoped agent rules and acceptance checklist.
- `sentinel-api` FastAPI service implementing `case-api.v1` routes with PostgreSQL-backed cases, messages, immutable input snapshots, durable ordered events (JSON + SSE), workflow outbox, and action index.
- Fixture and real-peer adapters for workflow, evidence, action-ledger, and verifier; local stub matrix under `tests/stubs/`.
- Decision proxy forwards authenticated supervisor bearer token and exact digest/revision; `VERIFIED_RESOLVED` requires a fresh matching trusted verifier assessment.
- Standalone `make check` (ruff + pytest against disposable Docker PostgreSQL).

### Implementation status

- Standalone module checks exercise fixture peers and local PostgreSQL.
- Assembled real-peer product evidence remains unverified until owner assembly.
