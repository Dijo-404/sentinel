# Sentinel independent task register

Status: revised proposal, not published. Existing task IDs and branch names are retained.

Every task has **zero completion prerequisites** and can start from the same planning baseline. Every task owns its build, contracts, stubs and tests. Phase labels describe product priority, not development order. Phase 2 tasks are optional for MVP release but can be developed now.

See [tasks.json](tasks.json), the [workflow design](agent-workflow-design.md), and the supplied [contract baseline](independent-task-contracts.md). GitHub owns assignment/status after publication; every issue URL below is still unpublished.

| ID | Independent deliverable | Lane | Phase | Owned root | Prerequisites | Optional | Branch | Issue |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| SN-001 | Build standalone module tooling and CI discovery | D | 1 | `tooling/workspace/` | None | No | `feat/sn-001-workspace` | Unpublished |
| SN-002 | Build contract conformance tooling from the supplied baseline | A | 1 | `packages/contract-checks/` | None | No | `feat/sn-002-contracts` | Unpublished |
| SN-003 | Build an independent tenant persistence toolkit | A | 1 | `packages/persistence/` | None | No | `feat/sn-003-persistence` | Unpublished |
| SN-004 | Build deterministic payment simulator and fault controls | B | 1 | `services/simulator/` | None | No | `feat/sn-004-simulator` | Unpublished |
| SN-005 | Build a standalone deterministic policy service | B | 1 | `services/policy/` | None | No | `feat/sn-005-policy` | Unpublished |
| SN-006 | Build an independent evidence and reconciliation service | B | 1 | `services/evidence/` | None | No | `feat/sn-006-evidence` | Unpublished |
| SN-007 | Build a standalone authenticated case API | A | 1 | `apps/api/` | None | No | `feat/sn-007-case-api` | Unpublished |
| SN-008 | Build an independent durable workflow worker | A | 1 | `services/workflow/` | None | No | `feat/sn-008-workflow` | Unpublished |
| SN-009 | Build the authoritative financial action-ledger service | B | 1 | `services/action-ledger/` | None | No | `feat/sn-009-reservations` | Unpublished |
| SN-010 | Build an independent refund dispatcher and recovery worker | B | 1 | `services/dispatcher/` | None | No | `feat/sn-010-dispatch-recovery` | Unpublished |
| SN-011 | Build an independent webhook and verification service | B | 1 | `services/verifier/` | None | No | `feat/sn-011-verification` | Unpublished |
| SN-012 | Build an independent customer and operator web shell | C | 1 | `apps/web/` | None | No | `feat/sn-012-ui-shell` | Unpublished |
| SN-013 | Build an independently previewable approval UI package | C | 1 | `packages/approval-ui/` | None | No | `feat/sn-013-approval-ui` | Unpublished |
| SN-014 | Build the four-journey integration harness independently | A | 1 | `integration/core/` | None | No | `feat/sn-014-core-integration` | Unpublished |
| SN-015 | Build a standalone telemetry package and example stack | D | 1 | `packages/telemetry/` | None | No | `feat/sn-015-observability` | Unpublished |
| SN-016 | Build an independent safety evaluation runner | D | 1 | `evals/core/` | None | No | `feat/sn-016-evaluation` | Unpublished |
| SN-017 | Build an independent optional Tamil voice adapter | C | 1 | `services/voice/` | None | Yes | `feat/sn-017-voice` | Unpublished |
| SN-018 | Build an independent replay and candidate-comparison runner | D | 1 | `replay/core/` | None | No | `feat/sn-018-replay` | Unpublished |
| SN-019 | Build a standalone MVP release-evidence verification kit | D | 1 | `release/mvp/` | None | No | `feat/sn-019-mvp-acceptance` | Unpublished |
| SN-020 | Build an independent FinHarness SDK around supplied ports | A | 2 | `packages/finharness-sdk/` | None | Yes | `feat/sn-020-finharness-extraction` | Unpublished |
| SN-021 | Build independent Sarvam reasoning and Indic context adapters | C | 2 | `packages/indic-context/` | None | Yes | `feat/sn-021-indic-context` | Unpublished |
| SN-022 | Build an independent shadow and sandbox harness runtime | A | 2 | `services/finharness-runtime/` | None | Yes | `feat/sn-022-harness-runtime` | Unpublished |
| SN-023 | Build an independent FinBench-Indic dataset and CLI | D | 2 | `benchmarks/finbench_indic/` | None | Yes | `feat/sn-023-finbench` | Unpublished |
| SN-024 | Build an independent harness telemetry extension | D | 2 | `packages/finharness-telemetry/` | None | Yes | `feat/sn-024-harness-observability` | Unpublished |
| SN-025 | Build an independent FinHarness replay and promotion gate | B | 2 | `replay/finharness/` | None | Yes | `feat/sn-025-harness-replay` | Unpublished |
| SN-026 | Build an independent sandbox pilot validation kit | B | 2 | `validation/sandbox-pilot/` | None | Yes | `feat/sn-026-sandbox-pilot` | Unpublished |

## Independence checklist

- Each PR implements a module-local `Makefile` with `check`; `make -C <owned-root> check` must pass without any other task implementation. These commands do not exist yet.
- Each module owns its manifest/lockfile, migrations if needed, configuration, README, fixtures and typed boundary validation.
- Consumed interfaces are supplied ports with local stubs, not task prerequisites. Never wait for SN-001 tooling, SN-002 validators, SN-003 database helpers, or an unfinished peer.
- Only SN-001 additionally owns `.github/workflows/module-checks.yml`; absent module tooling does not block another task's local check or review.
- The 26 primary roots do not overlap. No cross-service table writes or broad shared parent ownership is permitted.
- SN-009 alone owns authoritative financial approvals/reservations/action/outbox/audit transactions. Other workers use its ports, with local doubles during independent development.

## Completion and assembly

Component acceptance closes the task after its PR is merged. Product assembly and release evidence are separate owner-run checks. SN-014, SN-019 and SN-026 build integration/release/pilot **tools** against local reference peers; their tasks can finish without claiming the assembled product or an external pilot succeeded. Missing real peers must fail strict assembly/release checks explicitly.

After the one-time owner bootstrap of the accepted planning baseline, all admitted tasks can be ready together. No task requires another task to merge first. Preserve existing claims on publication reruns and deduplicate stable IDs against open and closed issues.
