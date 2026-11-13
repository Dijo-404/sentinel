# Changelog — SN-008 services/workflow

## Unreleased

### Changed — 14 November 2026

- Default auth map includes canonical `tok-workflow` / `tok-case-api` / `tok-verifier` plus legacy aliases; outbound bearer defaults to `tok-workflow`. Refs #77.

### Fixed

- Remove `X-Sentinel-Approval` forge path; DECISION resume uses ledger approval only.
- Outbox marks retry (not delivered) on `IDEMPOTENCY_CONFLICT`; revision bump only on `REVISION_CONFLICT`.
- `put_decision` only when job `created`; empty `case_ids` deny, `"*"` allows all.

## 0.1.0 — 2026-11-13

### Added

- SN-008 `sentinel-workflow` package implementing `workflow.v1` (`POST /v1/runs` → Ack 202).
- Typed LangGraph: load input, evidence, plan (fake/HTTP model), policy, approval interrupt, idempotent ledger propose/reserve, verify/wait, durable case-result outbox.
- Module-owned PostgreSQL schema (`workflow.jobs`, `result_outbox`, `decisions`) plus LangGraph `PostgresSaver` checkpointer.
- Local peer stubs (`tests/stubs/`) and real-peer HTTP adapters that surface unavailable/unauthorized/malformed failures.
- Contract snapshots and `make check` (ruff + pytest with disposable Docker Postgres).

### Notes

- Fake model is explicitly labeled; live model remains opt-in via `WORKFLOW_MODEL_MODE=http`.
- Real assembly against SN-005/006/007/009/011 peers is unverified.
