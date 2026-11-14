# SN-007 changelog

## Unreleased
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
