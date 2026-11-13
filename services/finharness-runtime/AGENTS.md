# Scoped agent rules: SN-022

Read [repository AGENTS.md](../../AGENTS.md) and this module's [README](README.md) before editing. These rules supplement the root instructions.

## Ownership

- Work only in `services/finharness-runtime/` and any exact extra paths listed in the task. No broad parent-directory ownership.
- Own the module's manifest/lockfile, configuration, migrations, code, contract snapshots, tests, fixtures, README and changelog.
- No task-completion prerequisite; use local port doubles. Never wait for another agent's implementation or modify another module's state to make tests pass.
- Use branch `feat/sn-022-harness-runtime` or an explicitly recorded alternative and a separate worktree.

## Architecture and contracts

- Business rules and use cases depend on narrow injected ports. Framework/provider/storage details stay in adapters and composition.
- Consume the pinned `sentinel.task-contracts.v1` input from the task. Record SHA-256 `0c728513e8b4ec0f34bcef63faa0207160d45cc7f20f872c1d9136ca7e252ffa`.
- No deep sibling imports, shared root application lockfile, cross-service SQL or unreviewed required contract changes.
- Real-peer failure must stay visible; never silently enable fixture fallback. Keep optional ports optional in assembled MVP mode.
- Preserve the single action-ledger authority, authenticated scope and approval, integer money, stable references, financial audit and verified closure rules.

## Checks and handoff

- Implement `make -C services/finharness-runtime check` with meaningful behavior/negative tests and standalone setup. It is currently a planned command, not a passing implementation.
- Run root `make check`, update [CHANGELOG.md](CHANGELOG.md), and record exact observed commands/results and fixture/real evidence.
- Keep progress/claims in the GitHub issue. Move to review with a PR using `Refs #N`; owner merges and accepts component evidence.
- Do not claim assembled product/pilot success from module or fixture checks.
