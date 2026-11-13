# SN-013 — Build an independently previewable approval UI package

**State:** scaffold and task instructions only. No implementation, dependency installation, module check target or product result is claimed.

**Owned root:** `packages/approval-ui/`
**Branch:** `feat/sn-013-approval-ui`
**Lane:** C · **Phase:** 1 · **Priority:** P0 · **Optional for MVP:** no

## Outcome

Build an embeddable typed approval/evidence component with its own preview and injected authorized client. Own its manifest/lockfile, fixtures and browser checks; do not edit or require the web shell.

## Independence

No task-completion prerequisites. This module must install, run its local checks, and be reviewable with every other Sentinel task implementation absent. Use explicit local port doubles rather than another developer's server or an unfinished sibling import. Phase and task number do not establish build order.

Read [root agent rules](../../AGENTS.md), [claim/PR workflow](../../CONTRIBUTING.md), [architecture](../../docs/architecture.md), and [testing](../../docs/testing.md). The [task register](../../docs/task-register.md) links the live issue once published.

## Ownership and interfaces

- `packages/approval-ui/**`

- Produces: `approval-ui.v1`
- Consumes: `case-api.v1`, `action-ledger.v1`
- Optional consumed interfaces: None

Contract input: [baseline](../../docs/independent-task-contracts.md) · `sentinel.task-contracts.v1` · SHA-256 `0c728513e8b4ec0f34bcef63faa0207160d45cc7f20f872c1d9136ca7e252ffa`.

Implement the exact supplied routes, request/response types, auth context, canonical digest and state/idempotency behavior for the relevant ports. Keep typed snapshots and compatibility examples in this module. The contract-checker/SDK implementation is not required.

### Required local peer doubles

- `case-api.v1` under `tests/stubs/`: valid, unavailable, malformed, unauthorized_or_out_of_scope.
- `action-ledger.v1` under `tests/stubs/`: valid, unavailable, malformed, unauthorized_or_out_of_scope.

## Implementation layout

Baseline category: TypeScript UI package with independent preview.

Use module-local dependency declarations and a reproducible lockfile, configuration example, tests, README and changelog. Stateful components own local migrations and a test database. No root application install or shared migration chain is allowed.

Keep deterministic business rules/types separate from application use cases/ports and external adapters. Wire adapters at one composition entry point. Introduce only directories that contain real responsibilities; the repository does not pre-generate empty layers. See the architecture and folder guides for language-specific layouts.

## Deliverables

- [ ] Local dependency manifest and lockfile; configuration example; Makefile check target; README with standalone setup and run/preview when applicable.
- [ ] Task-owned typed contract snapshots, fixtures, peer stubs, implementation, tests, and migrations/state setup where applicable.
- [ ] Real-peer adapter and compatibility checklist; no direct import of an unfinished sibling implementation.
- [ ] Update the local README/configuration and CHANGELOG.md with actual behavior and limitations.

## Acceptance criteria

- [ ] Preview fixtures show exact amount/transaction, policy version, evidence age, digest, expiry and reviewer identity; approve/reject submits the supplied digest/revision.
- [ ] Expired, stale, unauthorized, cross-tenant and 409 decision responses are handled accessibly without a live API or sibling UI package.
- [ ] All standalone checks pass using only the owned module, supplied baseline inputs, and local fixtures/stubs; no predecessor merge or root workspace tool is required.

## Planned local commands

The owning task must implement and document dependency setup, a local run/preview command where applicable, and this check target. It does not exist yet:

```sh
make -C packages/approval-ui check
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
