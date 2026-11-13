# Sentinel independent agent development workflow

Date: 13 November 2026. Status: approved independent-task design. Repository setup follows the owner's instruction to proceed; observed publication/enforcement details are recorded in [setup evidence](repository-setup.md).

## Intent and current state

Use Monolith's GitHub claim, branch, PR, and owner-review process for Sentinel. The user requires every task to be independently buildable: agents must not wait for another task to finish. This revision replaces the earlier sequential foundation and Phase 2 gates.

The user has created a shared `agents` issue view. Its URL and saved filter remain unverified. Earlier inspection found no commits, remote branches, issues, or custom labels. The existing source specifications and pitch PDF remain intact. The PDF was identified but not reviewed for this workflow proposal.

## Independence is the acceptance condition

Every task has zero task-completion prerequisites: `depends_on: []`. Each owns a separate directory, build manifest/lockfile, local configuration, contract snapshots, fixtures/stubs, tests, and documented check entry point. A service runs against local stub peers; a UI component has its own preview; a library or tool has its own executable test harness.

Each PR must build and pass its own acceptance checks when **none of the other 25 task implementations exists**. It may use standard tools and its own PostgreSQL/container dependencies. It must not import an unfinished sibling package, call another developer's running service, require a root workspace manifest, or wait for another task's migration/CI/contract package.

Not every deliverable needs a network service. Policy, SDK, context, telemetry, UI components, and evaluation libraries can be independently packaged modules. Runtime services expose narrow APIs. This satisfies independent development without turning every function into a separately deployed service.

The tradeoff is explicit: agents maintain local fixtures and boundary adapters. Contract conformance and later assembly checks catch mismatches. Standalone acceptance proves the component; assembled evidence proves the product.

## Baseline inputs available to every agent

[Independent task contracts](independent-task-contracts.md) defines the initial versioned wire/port contracts and safety invariants now. Its content hash is recorded in every task. Publish the relevant contract definitions and examples with each issue; do not tell an agent to wait for SN-002 to define them.

The baseline includes exact core service routes, request/response types, synthetic authentication context, canonical digest fixtures, and API-owned case-result propagation. SN-008 owns the Phase 1 model adapter; optional SN-021 is not an MVP dependency. Task `optional_consumes` explicitly marks integrations such as voice that may stay disabled in assembly.

Each agent implements its own typed boundary validation from that supplied baseline. Shared implementation packages are optional conveniences, never prerequisites for starting or finishing another task. The contract-checking task builds reusable validators against the existing baseline rather than owning a future contract freeze.

A task must include:

- Its input and output contracts, required error/status behavior, and exact baseline version/hash.
- Local deterministic stubs for every peer it consumes, including unavailable, malformed, delayed, and unauthorized responses where relevant.
- Its own implementation, dependency declarations/lockfile, configuration example, tests, and README under its owned root.
- A module-local `Makefile` with `check`, plus a local run/preview command when applicable. These commands are requirements to implement, not currently executable project features.
- A real-peer adapter using configurable endpoints or injected ports. Stubs remain explicit local-test fixtures; real-peer mode fails clearly if a peer is unavailable.
- Standalone evidence and a separate assembly checklist. Missing production peers are not a task blocker.

## Approaches and scope

The selected approach keeps Monolith's shared GitHub coordination while replacing task dependencies with independent packages and contract stubs. Keeping the old sequential foundation would conflict with the user's correction. Creating 26 mandatory network services would add operational coupling without improving independent development.

This design governs coordination and component boundaries. The approved repository setup installs documentation/scaffolds and publishes tasks; component implementations, service deployment, teammate messages and application PR merges remain outside setup scope. The existing product specifications remain historical source material.

Phase 1 versus Phase 2 describes product priority and release eligibility, not start order. Phase 2 SDK/runtime/context/benchmark modules can be built now against the supplied ports and local fakes. They remain optional for the MVP and disabled in the assembled product until reviewed. No task waits for SN-019, and no task assumes an existing implementation can already be extracted.

## Runtime ownership and financial safety

One action-ledger boundary owns approval records, payment eligibility/reservations, immutable action intent, stable operation references, dispatch leases, transactional outbox, and financial audit. These records participate in one local PostgreSQL transaction. Never split the reservation/outbox invariant across service databases.

The dispatcher consumes ledger-issued, scope-bound commands and is the only payment-write adapter. It does not own a second refund executor, mint a new reference after a timeout, or directly edit ledger tables. The verifier owns its inbox/recheck state and submits authenticated evidence to ledger transition APIs. Case, evidence, and workflow services own their own state and migrations; they do not read/write one another's tables.

A common PostgreSQL server is allowed in a local deployment, but schemas and credentials remain separately owned. Each task supplies its own test database setup without depending on the persistence-toolkit task.

Models propose; trusted identity, deterministic controls, exact approval, and transactional execution authorize. Use integer minor units, original payment destinations, tenant-scoped evidence, immutable digests, stable references, and bounded retries. Keep accepted, pending, provider-confirmed, and credit-confirmed outcomes distinct. Unknown outcomes retain reservations and reconcile by the original reference.

Use synthetic identities and simulated payment writes. No production payment credentials or real-money transfers are required. Financial audit is unsampled; telemetry is redacted. No fixture, replay, model stub, or component check is evidence of live provider behavior or assembled product readiness.

## File ownership

The [task plan](tasks.json) and [register](task-register.md) define 26 disjoint primary roots. Agents own everything required for their local build inside that root, including tests, schemas, migrations, lockfiles, fixtures, and docs.

- No task owns a broad parent directory containing another task's root.
- SN-001 owns optional CI discovery/aggregation and its templates; other tasks run their local checks before this tooling exists.
- SN-012 owns the main web shell. SN-013 owns an independently previewable approval UI package; the shell uses a documented component slot and a local stub until a compatible package is selected.
- SN-014 owns the integration harness, adapters, and scenario drivers. It does not edit API/workflow/UI source files belonging to other tasks.
- SN-015 and SN-024 own separate telemetry packages and local example stacks. Neither owns a global `infra/**` parent.
- SN-019 owns the release verification kit. It consumes evidence through a documented manifest rather than editing shared README/demo files.
- Each component owns its migrations. Only the action ledger may migrate its financial transaction tables.

Root tooling must discover modules already present and run their declared checks. Absent modules do not fail unrelated PRs. A change must not force all packages into a new root lockfile or make its standalone check depend on the aggregator.

## Shared GitHub task state

GitHub issues own live status, assignees, claims, blockers, PR links, and updates. `docs/tasks.json` owns versioned scope, contracts, paths, standalone acceptance, and assembly expectations. `docs/task-register.md` records published issue URLs. Do not put changing assignments/status in the versioned plan or blindly recreate issues.

Every issue receives `agents` and exactly one status:

| Label | Meaning |
| --- | --- |
| `status:backlog` | Task not yet admitted to the queue or scope/contract needs clarification. No automatic predecessor gate. |
| `status:ready` | Self-contained scope, baseline contract, fixtures, and owned root are supplied; available to claim. |
| `status:in-progress` | One agreed human/agent pair works in its own branch/worktree. |
| `status:blocked` | A real scope/contract/environment blocker is recorded. An unfinished peer alone is not a blocker. |
| `status:review` | Standalone implementation, PR, checks, and evidence are ready for owner review. |
| `status:done` | PR merged and component acceptance approved; issue closed. Assembly readiness is separate. |

Lane, priority, phase, and optional labels describe planning, not a dependency graph. Admitted tasks can enter `status:ready` together when the reviewed planning baseline and issues exist. There is no post-merge downstream-readiness transition.

Use the existing shared view with this filter, or [the equivalent queue](https://github.com/Dijo-404/sentinel/issues?q=is%3Aissue%20is%3Aopen%20label%3Aagents):

```text
repo:Dijo-404/sentinel is:issue is:open label:agents
```

Extra filters: `label:status:ready no:assignee`, `assignee:@me`, `label:status:blocked`. The saved view organizes tasks; it does not dispatch agents automatically.

## Claim, work, and PR

1. Read repository instructions, the task, latest comments/assignees/PRs, and the supplied contract baseline.
2. Select an unclaimed ready task. Check its root for competing ownership; do not look for predecessor task completion.
3. Assign the accountable human and post an agent/session claim. Recheck assignment and comments; GitHub assignment is not an atomic lock. Resolve competing claims before editing.
4. Start its branch from the accepted baseline/current `origin/main` in an independent worktree. Never switch another agent's working directory.
5. Build inside the owned root with local peer stubs. Include the real-peer adapter, but make component checks independent of peer implementation/availability.
6. Update GitHub when blocked, handing off, or ready, and at least once per working hour. Record next action, branch, pushed commit, exact checks, baseline hash, and real versus stub evidence.
7. Integrate current `origin/main`, rerun the component checks, push, and open a PR with `Refs #N`. Do not require unrelated tasks to merge first.
8. Move to review. The repository owner reviews and merges into `main`; agents do not push to `main`, merge, or enable auto-merge.
9. After merge and standalone acceptance, close the component task. Record unverified peer integration separately; do not call the product release complete.

Claim/handoff fields:

```text
Task and status:
Human owner; agent/session; UTC timestamp:
Branch/worktree; pushed commit/PR:
Owned root; contract baseline version/hash:
Consumed interfaces and local stubs:
Completed:
Standalone checks and observed results:
Real-peer assembly evidence or not yet exercised:
Actual blocker, next action, next update:
```

Use body files for multiline GitHub updates. Local agent memory never replaces shared issue updates.

## Contract changes without waiting

Implement the supplied baseline first. An agent may add a backwards-compatible optional field or new versioned endpoint in its own boundary, with fixtures and documentation. Keep the baseline endpoint working so peer agents can continue independently.

Do not silently change required fields, meanings, digests, enum semantics, or monetary rules. Propose a versioned change on the affected issues and provide a compatibility adapter. A peer can finish against the baseline while a newer contract is discussed. Never use a mock to relax authorization or financial invariants in real mode.

## Assembly and release evidence

SN-014 builds a scenario/integration runner now using its own reference peers; it also supports configured real service endpoints. SN-019 builds a release-evidence validator now with both valid and incomplete synthetic evidence manifests. SN-026 builds a sandbox load/recovery/rollback validation kit now. These are independent tool deliverables, not tasks whose completion claims the product or a live pilot has shipped.

Their standalone checks must verify missing peers/evidence fail explicitly, and fixture evidence cannot be promoted to real-peer evidence. Normal component CI can exercise fixtures; an explicit assembled-release run must reject fixture substitutes for required real component evidence.

The owner later selects compatible component versions and runs the assembled checks. The four Phase 1 journeys, database concurrency, approval, timeout recovery, webhook/recheck behavior, trace, evaluation, and replay evidence must pass before MVP release acceptance. Phase 2 activation and an external sandbox pilot remain separately reviewed rollout decisions, not development prerequisites.

## Approved repository setup

Install `AGENTS.md`, `CONTRIBUTING.md`, issue/PR templates, and an honest planning-state README. Preserve the supplied RTK include and source specifications. Templates must require owned root, baseline hash, consumed/produced ports, local stubs, standalone commands/evidence, real-peer adapter, and assembly limits; they must not require a predecessor merge.

The owner establishes an accepted initial `main` because the repository has no commits. This is a one-time repository baseline, not a task that blocks the other 25 tasks. Every task branches from that same starting point and carries its own build setup. Root CI installation is not a readiness gate.

Create missing labels and task issues only after checking open and closed issues for stable IDs. Publish the baseline definitions/examples in each issue and mark all admitted tasks ready together. Update the register with actual issue URLs through the agreed PR process. Verify the queue; if saved-view editing is unavailable, provide the exact filter without claiming it was applied.

Configure branch protection only if supported and authorized. Use actual checks introduced by the optional aggregator, not fictional global tests that cannot run before all modules exist.

## Acceptance for this revised plan

- Every task has empty `depends_on`, one disjoint owned root, a pinned baseline, explicit peer stubs, and standalone checks.
- Phase labels and task numbers never force development ordering; optional Phase 2 work can start independently.
- Every component can be reviewed and merged without another task's source, root manifest, schema, running service, or CI implementation.
- Contract checking, persistence, observability, integration, release evidence, and pilot validation are useful standalone packages/tools rather than hidden sequential gates.
- Financial transaction ownership and real-peer evidence remain strict. Independent development does not imply an already working assembled product.
- Repository publication/bootstrap is the explicitly approved one-time setup action. No existing source specification is rewritten; subsequent component work uses owner-reviewed PRs.
