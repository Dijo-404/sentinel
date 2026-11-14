# Scoped agent rules: assistant.v1

Read [repository AGENTS.md](../../AGENTS.md) and this module's [README](README.md) before editing. These rules supplement the root instructions.

## Ownership

- Work only in `services/assistant/` and any exact extra paths listed in the task.
- Own the module's manifest/lockfile, configuration, migrations, code, contract snapshots, tests, fixtures, README and changelog.
- No task-completion prerequisite; use local doubles. Never wait for another agent's implementation or modify another module's state to make tests pass.

## Architecture and contracts

- Business rules and use cases depend on narrow injected ports. Framework/provider/storage details stay in adapters and composition.
- No deep sibling imports, shared root application lockfile, cross-service SQL or unreviewed required contract changes.
- Real-peer failure must stay visible; never silently enable fixture fallback.
- No money ledger writes. Messages stay `evidence_mode=sandbox` unless a later authorized path changes labeling.

## Checks and handoff

- Run `make -C services/assistant check` for module-local evidence. Keep it green on every change.
- Update [CHANGELOG.md](CHANGELOG.md) and record exact observed commands/results.
- Do not claim assembled product/pilot success from module or fixture checks.
