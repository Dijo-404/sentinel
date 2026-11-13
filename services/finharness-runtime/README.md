# SN-022 — Build an independent shadow and sandbox harness runtime

**State:** scaffold and task instructions only. No implementation, dependency installation, module check target or product result is claimed.

**Owned root:** `services/finharness-runtime/`
**Branch:** `feat/sn-022-harness-runtime`
**Lane:** A · **Phase:** 2 · **Priority:** P1 · **Optional for MVP:** yes

## Outcome

Implement pinned-case runtime and injected SDK-compatible/model/safety ports with local doubles. Add read-only shadow comparison, restart behavior and guarded sandbox routing; no existing application, extracted SDK or Phase 1 merge is required.

## Independence

No task-completion prerequisites. This module must install, run its local checks, and be reviewable with every other Sentinel task implementation absent. Use explicit local port doubles rather than another developer's server or an unfinished sibling import. Phase and task number do not establish build order.

Read [root agent rules](../../AGENTS.md), [claim/PR workflow](../../CONTRIBUTING.md), [architecture](../../docs/architecture.md), and [testing](../../docs/testing.md). The [task register](../../docs/task-register.md) links the live issue once published.

## Ownership and interfaces

- `services/finharness-runtime/**`

- Produces: `finharness-runtime.v1`
- Consumes: `finharness-sdk.v1`, `indic-context.v1`, `evidence.v1`, `policy.v1`, `action-ledger.v1`, `verifier.v1`
- Optional consumed interfaces: None

Contract input: [baseline](../../docs/independent-task-contracts.md) · `sentinel.task-contracts.v1` · SHA-256 `0c728513e8b4ec0f34bcef63faa0207160d45cc7f20f872c1d9136ca7e252ffa`.

Implement the exact supplied routes, request/response types, auth context, canonical digest and state/idempotency behavior for the relevant ports. Keep typed snapshots and compatibility examples in this module. The contract-checker/SDK implementation is not required.

### Required local peer doubles

- `finharness-sdk.v1` under `tests/stubs/`: valid, unavailable, malformed, unauthorized_or_out_of_scope.
- `indic-context.v1` under `tests/stubs/`: valid, unavailable, malformed, unauthorized_or_out_of_scope.
- `evidence.v1` under `tests/stubs/`: valid, unavailable, malformed, unauthorized_or_out_of_scope.
- `policy.v1` under `tests/stubs/`: valid, unavailable, malformed, unauthorized_or_out_of_scope.
- `action-ledger.v1` under `tests/stubs/`: valid, unavailable, malformed, unauthorized_or_out_of_scope.
- `verifier.v1` under `tests/stubs/`: valid, unavailable, malformed, unauthorized_or_out_of_scope.

## Implementation layout

Baseline category: Python service/library/tool.

Use module-local dependency declarations and a reproducible lockfile, configuration example, tests, README and changelog. Stateful components own local migrations and a test database. No root application install or shared migration chain is allowed.

Keep deterministic business rules/types separate from application use cases/ports and external adapters. Wire adapters at one composition entry point. Introduce only directories that contain real responsibilities; the repository does not pre-generate empty layers. See the architecture and folder guides for language-specific layouts.

## Deliverables

- [ ] Local dependency manifest and lockfile; configuration example; Makefile check target; README with standalone setup and run/preview when applicable.
- [ ] Task-owned typed contract snapshots, fixtures, peer stubs, implementation, tests, and migrations/state setup where applicable.
- [ ] Real-peer adapter and compatibility checklist; no direct import of an unfinished sibling implementation.
- [ ] Update the local README/configuration and CHANGELOG.md with actual behavior and limitations.

## Acceptance criteria

- [ ] Local shadow execution has no write adapter/credentials/notification capability and cannot send a second refund.
- [ ] Version pinning, new-case rollout/rollback and unknown-action reconciliation tests survive switch changes/restart; real adapters fail closed when peers are absent.
- [ ] All standalone checks pass using only the owned module, supplied baseline inputs, and local fixtures/stubs; no predecessor merge or root workspace tool is required.

## Planned local commands

The owning task must implement and document dependency setup, a local run/preview command where applicable, and this check target. It does not exist yet:

```sh
make -C services/finharness-runtime check
```

Run root `make check` as well. Root checks validate repository metadata and tools; they do not implement or substitute for this component's behavior tests. External provider credentials are optional for local fixture checks.

## Test and failure requirements

- Exercise observable acceptance behavior and meaningful invalid, unavailable, malformed and unauthorized boundary cases.
- Use real PostgreSQL tests for financial locking/transactions, durable checkpoints or other database behavior that an in-memory double cannot establish.
- Label fixtures/simulated providers/fake or live inference precisely. A real-peer adapter must not silently convert peer failure into fixture success.
- Confirm the module works with sibling implementations absent and record exactly which local doubles/databases were used.

## Evidence and review

- Exact standalone setup/check commands, actual results and pinned contract baseline hash.
- Proof the check uses no sibling source or running Sentinel peer; identify all local stubs and database dependencies.
- PR/artifact links and separate real-component, payment-simulator, fake/live model and assembly evidence status.

Open a PR targeting main with `Refs #<issue>` and the PR template. Update the issue to review. Owner review/merge and accepted standalone evidence close the component issue. Agents never push main, merge or enable auto-merge.

## Assembly limits

- A separate owner-run assembly selects compatible real component versions and exercises the declared interfaces; record exact version, mode, checks and results.
- Missing real peers do not block this component PR. Mark real-peer integration unverified until exercised; fixture peers cannot satisfy product release evidence.
