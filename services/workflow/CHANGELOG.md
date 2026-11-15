# Changelog — SN-008 services/workflow

## Unreleased

### Fixed — 15 November 2026 (Refs #144)

- Ledger/policy/verifier/risk `PeerError` escalations keep the peer code:
  `reason_code` is `<PEER>_<CODE>` (e.g. `LEDGER_APPROVAL_EXPIRED`) when the code
  matches `[A-Z][A-Z0-9_]{1,63}`, else the previous `*_PEER_FAILURE` /
  `RISK_PEER_UNAVAILABLE`. Code, status and message are logged at warning level.
- Redelivering a `job_key` whose job `failed` (same payload digest) re-executes it
  via an atomic `failed`→`running` UPDATE; completed/running jobs stay idempotent.
  DECISION ledger-approval lookup now runs inside the failure handler, so a ledger
  outage marks the job `failed` instead of leaving it `accepted` forever.

### Added

- Authenticated `POST /v1/workflow/risk-resume` for risk clearance events; starts
  re-evaluation (`START`) without granting financial approval.
- Risk hold port (`GET /v1/risk/cases/{case_id}/blocks` via fixture/HTTP); fail
  closed before ledger propose/reserve when restriction active or risk peer down.

### Fixed

- Reserve after approval sends explicit `order_reference` from case input
  (and stashes it on the local proposal for restart); missing value escalates
  `ORDER_REFERENCE_REQUIRED`. HTTP reservation JSON includes the top-level field.
- Refuse non-loopback HTTP bind while demo/sandbox bearer tokens remain configured.

### Changed — 14 November 2026

- Default auth map includes canonical `tok-workflow` / `tok-case-api` / `tok-verifier` plus legacy aliases; outbound bearer defaults to `tok-workflow`. Refs #77.

### Fixed

- Remove `X-Sentinel-Approval` forge path; DECISION resume uses ledger approval only.
- Outbox marks retry (not delivered) on `IDEMPOTENCY_CONFLICT`; revision bump only on `REVISION_CONFLICT`.
- `put_decision` only when job `created`; empty `case_ids` deny, `"*"` allows all.
- Outbox `mark_retry` sets `status=failed` after `WORKFLOW_OUTBOX_MAX_ATTEMPTS` (default 10); `pending()` returns only retryable rows (optional `available_at` backoff).

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
