# Working on Sentinel

## Read first

1. [README.md](README.md), [CONTRIBUTING.md](CONTRIBUTING.md), and the assigned GitHub issue, including current comments, assignees, and linked PRs.
2. [Architecture](docs/architecture.md), [repository structure](docs/repository-structure.md), [testing](docs/testing.md), and [configuration](docs/configuration.md).
3. Your module's `AGENTS.md`, `README.md`, and `CHANGELOG.md`.
4. The task's record in [docs/tasks.json](docs/tasks.json) and the pinned [contract baseline](docs/independent-task-contracts.md).
5. The relevant sections of [Phase 1](docs/sentinel-p1.md) and [Phase 2](docs/sentinel-p2.md). These specifications describe planned capabilities, not implemented behavior. Sentinel is the project name; older ResolveOps terminology is historical.

## Local command-output guidance

Use `rg` for search, bound command output, retain decisive errors, and never print credentials. Keep machine-local RTK instructions in each agent's global configuration rather than importing files outside this repository. No project check depends on RTK being installed.

## Coordinate through GitHub

- Use the [Agents queue](https://github.com/Dijo-404/sentinel/issues?q=is%3Aissue%20is%3Aopen%20label%3Aagents). GitHub owns assignment, live status, blockers and handoffs. Local memory is personal, not shared task state.
- All tasks are independently buildable. Do not wait for SN-001 tooling, SN-002 validators, SN-003 helpers, an optional Phase 2 module, or a peer implementation.
- Claim one `status:ready` issue after reading/rechecking assignees and comments. One accountable human and one active agent/session own a task. Assignment is not an atomic lock; resolve competing claims before editing.
- Use the issue's feature branch and an independent worktree. Never switch another agent's working directory.
- Record human, agent/session, UTC time, branch/worktree, owned root, baseline hash, next action and update time. Update at transitions and at least once per working hour.
- Maintain exactly one `status:*` label. An unfinished peer is not a blocker: use the supplied contracts and local doubles.
- Work only in listed paths. Each module owns its source, dependencies, lockfile, configuration, migrations, tests, fixtures, README and changelog. Coordinate a scope change on affected issues before editing outside ownership.
- Do not change root tooling/policies, source specifications, another module, or the global changelog from a component task. Record a separate proposal when a shared change is necessary.

## Clean architecture

- Keep business invariants in framework-free domain code; application use cases depend on small ports. HTTP, SQLAlchemy, LangGraph, model/provider SDKs, telemetry exporters and filesystem access belong in adapters/composition.
- Introduce a layer when a real rule or external boundary needs it. Do not generate empty layers, generic service frameworks, global registries, or abstractions for hypothetical extensions.
- No deep imports into another module, cross-service table access, root application manifest, or shared lockfile. Consume a versioned wire contract or injected public port.
- Keep each module installable and testable with every other task implementation absent. Module-local `make check` is required evidence for the owned root; root `make check` validates repository metadata only.
- Real-peer mode must reject unavailable, malformed, unauthorized or incompatible peers. Never silently fall back to a fixture in a real run.
- Preserve compatible contract semantics. Add versioned adapters for breaking changes; do not force other agents to stop work.

## Financial and data boundaries

- Use synthetic data and simulator payment writes. No production payment credentials, real-money movement, private customer data or external pilot activity without separate authorization.
- Models propose. Authenticated server identity, deterministic policy, exact supervisor approval, transactional reservation and verified outcomes govern money.
- SN-009 alone owns authoritative approval, eligibility/reservation, action, operation/provider reference, outbox, lease and financial audit state. Preserve their atomic transaction. No other module edits those tables or creates a second executor/ledger.
- The dispatcher is the only provider-write adapter. On timeout/crash, reconcile the original stable reference; never mint another refund ID or release a reservation because a lease expired.
- Use integer minor units and explicit currency. Enforce tenant/subject scope, original payment route, fresh evidence, immutable digest/version, expiry, and completed + pending + reserved limits.
- A pending refund or provider confirmation is not proof of customer credit. Resolve only after the configured authoritative postconditions pass. Escalation is not resolution.
- Financial audit is unsampled and distinct from telemetry. Redact secrets and identifiers; label fixture, simulated, recorded and live evidence accurately.

## Verification and handoff

- Implement acceptance tests for real behavior and relevant failure/concurrency boundaries. Run module-local checks and root `make check`; root checks validate repository metadata, not product safety.
- Update the owned module's changelog and documentation. Include exact commands, actual outcomes, contract hash, fixture/live modes and untested assembly boundaries in the PR.
- Open a PR into `main` with `Refs #N`; move the issue to `status:review`. The owner reviews and merges. Agents must not push to `main`, merge PRs, or enable auto-merge.
- The user's initial empty-repository bootstrap authorization is a one-time exception for this setup. It does not authorize future component agents to update `main` directly.
- Close the component task after merge and accepted standalone evidence. Product assembly/release and external pilot acceptance remain separate owner decisions. Do not use a passing fixture or metadata check as release evidence.
