# Scoped agent rules: platform-ai (portal wave 4)

Read [repository AGENTS.md](../../AGENTS.md) and this module's [README](README.md) before editing. These rules supplement the root instructions.

## Ownership

- Work only in `services/platform-ai/` and any exact extra paths listed in the task. No broad parent-directory ownership.
- Own the module's manifest/lockfile, configuration, migrations, code, contract snapshots, tests, fixtures, README and changelog.
- No task-completion prerequisite; use local doubles. Never wait for another agent's implementation or modify another module's state to make tests pass.
- Use branch `feat/portal-wave4-intel-voice-approval` or an explicitly recorded alternative and a separate worktree.

## Architecture and contracts

- Business rules and use cases depend on narrow injected ports. Framework/provider/storage details stay in adapters and composition.
- Consume the pinned `sentinel.task-contracts.v1` input. Record SHA-256 `0db3ba2bba994f10d3060bc7173035360c15ffe23189cea409f7327e23c36feb`.
- Metadata only: AI config and run rows. Never mint refunds, call ledger decide, or store money fields.
- No deep sibling imports, shared root application lockfile, cross-service SQL or unreviewed required contract changes.
- Real-peer failure must stay visible; never silently enable fixture fallback.

## Checks and handoff

- Run `make -C services/platform-ai check` for module-local evidence. Keep it green on every change.
- Update [CHANGELOG.md](CHANGELOG.md) and record exact observed commands/results and fixture/real evidence.
- Do not claim assembled product/pilot success from module or fixture checks.
