# Portal DB-backed completion — program index

> **For agentic workers:** Execute **one wave plan at a time**. Do not treat this index as a single implementable task list.

**Spec:** `docs/superpowers/specs/2026-11-15-portal-db-backed-completion-design.md` (approved 2026-11-15)

## Wave plans

| Wave | Plan file | Status |
| --- | --- | --- |
| 0–1 Foundation + Merchant/Risk wire | `docs/superpowers/plans/2026-11-15-portal-wave0-1-foundation-merchant-risk.md` | **active** |
| 2 Ops case surfaces | TBD after wave 0–1 | pending |
| 3 Identity / auth / customer | TBD | pending |
| 4 Intel + voice + approval-ui | TBD | pending |
| 5 Admin remainder | TBD | pending |
| 6 Money-path E2E | TBD | pending |

## Global program constraints (all waves)

- No UI mock/fixture product rows; seed Postgres; fail closed in real-peers.
- SN-009 sole money authority; simulator only for payments.
- Real `packages/approval-ui` (wave 4+); real voice/Sarvam (wave 4+).
- Evaluations = extend `evals/core`; Observability = `packages/telemetry` + `services/observability`.
- One owned root / worktree / issue claim per implementer; no push to `main`.
