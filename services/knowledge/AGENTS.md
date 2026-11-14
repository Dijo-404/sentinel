# Scoped agent rules: knowledge.v1

Read [repository AGENTS.md](../../AGENTS.md) and this module's [README](README.md)
before editing. These rules supplement the root instructions.

## Ownership

- Work only in `services/knowledge/` and any exact extra paths listed in the task.
- Own the module's manifest/lockfile, configuration, migrations, code, contract
  snapshots, tests, fixtures, README and changelog.
- No task-completion prerequisite; use local doubles. Never wait for another agent's
  implementation or modify another module's state to make tests pass.

## Architecture and contracts

- Business rules and use cases depend on narrow injected ports. Framework/provider/
  storage details stay in adapters and composition.
- Consume the pinned `sentinel.task-contracts.v1` input from the task. Record SHA-256
  `0db3ba2bba994f10d3060bc7173035360c15ffe23189cea409f7327e23c36feb`.
- No deep sibling imports, shared root application lockfile, cross-service SQL or
  unreviewed required contract changes.
- Real-peer failure must stay visible; never silently enable fixture fallback.
- No money authority: never call ledger decide or mint refunds from this module.

## Checks and handoff

- Run `make -C services/knowledge check` for module-local evidence.
- Update [CHANGELOG.md](CHANGELOG.md) and record fixture/real evidence in the PR.
- Do not claim assembled product/pilot success from module or fixture checks.
