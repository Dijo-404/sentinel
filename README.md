# Sentinel

Sentinel is a planned AI teammate for payment operations: investigate exceptions, apply deterministic policy, obtain exact supervisor approval, execute through controlled simulator adapters, and verify outcomes before closure.

**Current state:** repository/agent workflow baseline and 26 independent component scaffolds. Application services, UI, SDK and benchmarks are assigned implementation tasks. No product runtime, live payment integration or benchmark results are claimed.

## Start here

- [Agent rules](AGENTS.md) and [contribution/claim workflow](CONTRIBUTING.md)
- [GitHub Agents queue](https://github.com/Dijo-404/sentinel/issues?q=is%3Aissue%20is%3Aopen%20label%3Aagents) and [task register](docs/task-register.md)
- [Clean architecture](docs/architecture.md), [folder structure](docs/repository-structure.md), [configuration](docs/configuration.md), and [testing](docs/testing.md)
- [Pinned interfaces](docs/independent-task-contracts.md) and [versioned task definitions](docs/tasks.json)
- [Changelog](CHANGELOG.md), [Phase 1 specification](docs/sentinel-p1.md), [Phase 2 extension](docs/sentinel-p2.md), and [pitch deck](docs/Sentinel_Pitch_Deck.pdf)

## Repository checks

Requires Python 3.11+ and GNU Make; no application dependencies or provider keys are needed:

```sh
make check
```

This runs metadata/documentation validation and repository-tool tests. It does not run application tests. Each component task provides its own dependency setup and `make -C <owned-root> check` target; those targets are not implemented by this scaffold.

## Independent component development

All 26 tasks can start from the same baseline. Each has separate ownership, manifests, tests, configuration, contract snapshots, local peer doubles and changelog. No task waits for another issue to finish. Phase 2 modules are optional for MVP release and may be developed independently now.

```text
apps/           Case API and web shell
services/       Simulation, policy, evidence, workflow, ledger, dispatch, verification, voice, optional runtime
packages/       Independently packaged contracts/persistence/UI/telemetry/SDK/context helpers
tooling/        Optional module-check aggregation
integration/    Four-journey scenario and assembly runner
evals/          Core deterministic evaluation runner
replay/         Isolated core and optional harness replay
benchmarks/     Optional FinBench-Indic
release/        MVP evidence-verification kit
validation/     Authorized sandbox-pilot validation kit
scripts/        Repository metadata and task-publication tools
tests/          Repository-tool regression tests only
docs/           Source specifications, contracts, architecture, task plan and issue map
```

Use module-local clean architecture: business rules and use cases depend on small ports; frameworks/storage/provider SDKs enter through adapters. One action-ledger boundary owns atomic financial state. No shared service tables, unfinished sibling imports, global application manifest or root lockfile.

Component PRs target `main`; the repository owner reviews and merges. Local stub checks prove a component, while separately run real-component assembly checks prove product behavior. All payment writes remain simulated unless the owner separately authorizes an external integration.
