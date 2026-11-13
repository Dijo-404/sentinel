# Sentinel independent task register

Status: published to GitHub on 13 November 2026. Task IDs and branch names remain stable; GitHub owns live assignment and status.

Every task has **zero completion prerequisites** and can start from the same planning baseline. Every task owns its build, contracts, stubs and tests. Phase labels describe product priority, not development order. Phase 2 tasks are optional for MVP release but can be developed now.

See [tasks.json](tasks.json), the [workflow design](agent-workflow-design.md), and the supplied [contract baseline](independent-task-contracts.md). GitHub owns live assignment/status; the issue URLs below identify the published tasks.

| ID | Independent deliverable | Lane | Phase | Owned root | Prerequisites | Optional | Branch | Issue |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| SN-001 | Build standalone module tooling and CI discovery | D | 1 | `tooling/workspace/` | None | No | `feat/sn-001-workspace` | [#1](https://github.com/Dijo-404/sentinel/issues/1) |
| SN-002 | Build contract conformance tooling from the supplied baseline | A | 1 | `packages/contract-checks/` | None | No | `feat/sn-002-contracts` | [#2](https://github.com/Dijo-404/sentinel/issues/2) |
| SN-003 | Build an independent tenant persistence toolkit | A | 1 | `packages/persistence/` | None | No | `feat/sn-003-persistence` | [#3](https://github.com/Dijo-404/sentinel/issues/3) |
| SN-004 | Build deterministic payment simulator and fault controls | B | 1 | `services/simulator/` | None | No | `feat/sn-004-simulator` | [#4](https://github.com/Dijo-404/sentinel/issues/4) |
| SN-005 | Build a standalone deterministic policy service | B | 1 | `services/policy/` | None | No | `feat/sn-005-policy` | [#5](https://github.com/Dijo-404/sentinel/issues/5) |
| SN-006 | Build an independent evidence and reconciliation service | B | 1 | `services/evidence/` | None | No | `feat/sn-006-evidence` | [#6](https://github.com/Dijo-404/sentinel/issues/6) |
| SN-007 | Build a standalone authenticated case API | A | 1 | `apps/api/` | None | No | `feat/sn-007-case-api` | [#7](https://github.com/Dijo-404/sentinel/issues/7) |
| SN-008 | Build an independent durable workflow worker | A | 1 | `services/workflow/` | None | No | `feat/sn-008-workflow` | [#8](https://github.com/Dijo-404/sentinel/issues/8) |
| SN-009 | Build the authoritative financial action-ledger service | B | 1 | `services/action-ledger/` | None | No | `feat/sn-009-reservations` | [#9](https://github.com/Dijo-404/sentinel/issues/9) |
| SN-010 | Build an independent refund dispatcher and recovery worker | B | 1 | `services/dispatcher/` | None | No | `feat/sn-010-dispatch-recovery` | [#10](https://github.com/Dijo-404/sentinel/issues/10) |
| SN-011 | Build an independent webhook and verification service | B | 1 | `services/verifier/` | None | No | `feat/sn-011-verification` | [#11](https://github.com/Dijo-404/sentinel/issues/11) |
| SN-012 | Build an independent customer and operator web shell | C | 1 | `apps/web/` | None | No | `feat/sn-012-ui-shell` | [#12](https://github.com/Dijo-404/sentinel/issues/12) |
| SN-013 | Build an independently previewable approval UI package | C | 1 | `packages/approval-ui/` | None | No | `feat/sn-013-approval-ui` | [#13](https://github.com/Dijo-404/sentinel/issues/13) |
| SN-014 | Build the four-journey integration harness independently | A | 1 | `integration/core/` | None | No | `feat/sn-014-core-integration` | [#14](https://github.com/Dijo-404/sentinel/issues/14) |
| SN-015 | Build a standalone telemetry package and example stack | D | 1 | `packages/telemetry/` | None | No | `feat/sn-015-observability` | [#15](https://github.com/Dijo-404/sentinel/issues/15) |
| SN-016 | Build an independent safety evaluation runner | D | 1 | `evals/core/` | None | No | `feat/sn-016-evaluation` | [#16](https://github.com/Dijo-404/sentinel/issues/16) |
| SN-017 | Build an independent optional Tamil voice adapter | C | 1 | `services/voice/` | None | Yes | `feat/sn-017-voice` | [#17](https://github.com/Dijo-404/sentinel/issues/17) |
| SN-018 | Build an independent replay and candidate-comparison runner | D | 1 | `replay/core/` | None | No | `feat/sn-018-replay` | [#18](https://github.com/Dijo-404/sentinel/issues/18) |
| SN-019 | Build a standalone MVP release-evidence verification kit | D | 1 | `release/mvp/` | None | No | `feat/sn-019-mvp-acceptance` | [#19](https://github.com/Dijo-404/sentinel/issues/19) |
| SN-020 | Build an independent FinHarness SDK around supplied ports | A | 2 | `packages/finharness-sdk/` | None | Yes | `feat/sn-020-finharness-extraction` | [#20](https://github.com/Dijo-404/sentinel/issues/20) |
| SN-021 | Build independent Sarvam reasoning and Indic context adapters | C | 2 | `packages/indic-context/` | None | Yes | `feat/sn-021-indic-context` | [#21](https://github.com/Dijo-404/sentinel/issues/21) |
| SN-022 | Build an independent shadow and sandbox harness runtime | A | 2 | `services/finharness-runtime/` | None | Yes | `feat/sn-022-harness-runtime` | [#22](https://github.com/Dijo-404/sentinel/issues/22) |
| SN-023 | Build an independent FinBench-Indic dataset and CLI | D | 2 | `benchmarks/finbench_indic/` | None | Yes | `feat/sn-023-finbench` | [#23](https://github.com/Dijo-404/sentinel/issues/23) |
| SN-024 | Build an independent harness telemetry extension | D | 2 | `packages/finharness-telemetry/` | None | Yes | `feat/sn-024-harness-observability` | [#24](https://github.com/Dijo-404/sentinel/issues/24) |
| SN-025 | Build an independent FinHarness replay and promotion gate | B | 2 | `replay/finharness/` | None | Yes | `feat/sn-025-harness-replay` | [#25](https://github.com/Dijo-404/sentinel/issues/25) |
| SN-026 | Build an independent sandbox pilot validation kit | B | 2 | `validation/sandbox-pilot/` | None | Yes | `feat/sn-026-sandbox-pilot` | [#26](https://github.com/Dijo-404/sentinel/issues/26) |
| SN-027 | Build independent merchant settlement reconciliation | B | 2 | `services/merchant-settlement/` | None | Yes | `feat/sn-027-merchant-settlement` | [#56](https://github.com/Dijo-404/sentinel/issues/56) |
| SN-028 | Build an independent merchant exception inbox | C | 2 | `services/merchant-inbox/` | None | Yes | `feat/sn-028-merchant-inbox` | [#57](https://github.com/Dijo-404/sentinel/issues/57) |
| SN-029 | Build independent merchant refund request workflow | B | 2 | `services/merchant-refunds/` | None | Yes | `feat/sn-029-merchant-refunds` | [#58](https://github.com/Dijo-404/sentinel/issues/58) |
| SN-030 | Build independent merchant dispute management | B | 2 | `services/merchant-disputes/` | None | Yes | `feat/sn-030-merchant-disputes` | [#59](https://github.com/Dijo-404/sentinel/issues/59) |
| SN-031 | Build independent merchant SLA and task management | A | 2 | `services/merchant-sla/` | None | Yes | `feat/sn-031-merchant-sla` | [#60](https://github.com/Dijo-404/sentinel/issues/60) |
| SN-032 | Build independent merchant analytics aggregates | D | 2 | `services/merchant-analytics/` | None | Yes | `feat/sn-032-merchant-analytics` | [#61](https://github.com/Dijo-404/sentinel/issues/61) |
| SN-033 | Build independent multilingual merchant communications | C | 2 | `packages/merchant-comms/` | None | Yes | `feat/sn-033-merchant-comms` | [#62](https://github.com/Dijo-404/sentinel/issues/62) |
| SN-034 | Build independent merchant team and role management | A | 2 | `services/merchant-teams/` | None | Yes | `feat/sn-034-merchant-teams` | [#63](https://github.com/Dijo-404/sentinel/issues/63) |

## Independence checklist

- Each PR implements a module-local `Makefile` with `check`; `make -C <owned-root> check` must pass without any other task implementation. These commands do not exist yet.
- Each module owns its manifest/lockfile, migrations if needed, configuration, README, fixtures and typed boundary validation.
- Consumed interfaces are supplied ports with local stubs, not task prerequisites. Never wait for SN-001 tooling, SN-002 validators, SN-003 database helpers, or an unfinished peer.
- Only SN-001 additionally owns `.github/workflows/module-checks.yml`; absent module tooling does not block another task's local check or review.
- The primary roots do not overlap. No cross-service table writes or broad shared parent ownership is permitted.
- SN-009 alone owns authoritative financial approvals/reservations/action/outbox/audit transactions. Other workers use its ports, with local doubles during independent development.

## Completion and assembly

Component acceptance closes the task after its PR is merged. Product assembly and release evidence are separate owner-run checks. SN-014, SN-019 and SN-026 build integration/release/pilot **tools** against local reference peers; their tasks can finish without claiming the assembled product or an external pilot succeeded. Missing real peers must fail strict assembly/release checks explicitly.

After the one-time owner bootstrap of the accepted planning baseline, all admitted tasks can be ready together. No task requires another task to merge first. Preserve existing claims on publication reruns and deduplicate stable IDs against open and closed issues.
