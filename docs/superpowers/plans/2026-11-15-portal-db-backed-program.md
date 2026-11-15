# Portal DB-backed completion — program index

> **For agentic workers:** Execute **one wave plan at a time**. Do not treat this index as a single implementable task list.

**Spec:** `docs/superpowers/specs/2026-11-15-portal-db-backed-completion-design.md` (approved 2026-11-15)

## Wave plans

| Wave | Plan file | Status |
| --- | --- | --- |
| 0–1 Foundation + Merchant/Risk wire | `docs/superpowers/plans/2026-11-15-portal-wave0-1-foundation-merchant-risk.md` | done (hardcode audit merged on branch) |
| 2 Ops case surfaces | `docs/superpowers/plans/2026-11-15-portal-wave2-ops-case-surfaces.md` | done |
| 3 Identity / auth / customer | `docs/superpowers/plans/2026-11-15-portal-wave3-identity-auth-customer.md` | done |
| 4 Intel + voice + approval-ui | `docs/superpowers/plans/2026-11-15-portal-wave4-intel-voice-approval.md` | done |
| 5 Admin remainder | `docs/superpowers/plans/2026-11-15-portal-wave5-admin-remainder.md` | done |
| 6 Money-path E2E | `docs/superpowers/plans/2026-11-15-portal-wave6-money-path-e2e.md` | done |

**Program status:** waves 0–6 complete. Assembled MVP / product release remains an **owner review** decision — harness PASS and `verify-wave6` are not release evidence.

## Global program constraints (all waves)

- No UI mock/fixture product rows; seed Postgres; fail closed in real-peers.
- SN-009 sole money authority; simulator only for payments.
- Real `packages/approval-ui` (wave 4+); real voice/Sarvam (wave 4+).
- Evaluations = extend `evals/core`; Observability = `packages/telemetry` + `services/observability`.
- One owned root / worktree / issue claim per implementer; no push to `main`.
