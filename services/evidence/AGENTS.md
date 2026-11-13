# Scoped agent rules: SN-006

Read [repository AGENTS.md](../../AGENTS.md) and this module's [README](README.md) before editing. These rules supplement the root instructions.

## Ownership

- Work only in `services/evidence/` and any exact extra paths listed in the task. No broad parent-directory ownership.
- Own the module's manifest/lockfile, configuration, migrations, code, contract snapshots, tests, fixtures, README and changelog.
- No task-completion prerequisite; use local port doubles. Never wait for another agent's implementation or modify another module's state to make tests pass.
- Use branch `feat/sn-006-evidence` or an explicitly recorded alternative and a separate worktree.

## Architecture and contracts

- Business rules and use cases depend on narrow injected ports. Framework/provider/storage details stay in adapters and composition.
- Consume the pinned `sentinel.task-contracts.v1` input from the task. Record SHA-256 `0db3ba2bba994f10d3060bc7173035360c15ffe23189cea409f7327e23c36feb`.
- No deep sibling imports, shared root application lockfile, cross-service SQL or unreviewed required contract changes.
- Real-peer failure must stay visible; never silently enable fixture fallback. Keep optional ports optional in assembled MVP mode.
- Preserve the single action-ledger authority, authenticated scope and approval, integer money, stable references, financial audit and verified closure rules.

## Checks and handoff

- Run `make -C services/evidence check` for module-local evidence. The target is implemented; keep it green on every change.
- Run root `make check`, update [CHANGELOG.md](CHANGELOG.md), and record exact observed commands/results and fixture/real evidence.
- Keep progress/claims in the GitHub issue. Move to review with a PR using `Refs #N`; owner merges and accepts component evidence.
- Do not claim assembled product/pilot success from module or fixture checks.
