# SN-002 changelog

## Unreleased

### Added — 13 November 2026

- Independently installable Python package, pinned local dependency lock, configuration example, CLI and module-local `make check`.
- Portable JSON Schema snapshots for 66 named wire types and all six action variants; exact source baseline, 31 route/auth rows and matching operation examples.
- Strict UTF-8/integer JSON validation, exact action canonical bytes/digests, nested digest/approval checks, original evidence byte validation, state/version enums and expiry ordering.
- Synthetic wire/malformed-input fixtures, eight canonical vectors, scoped retry conflict captures, and conservative optional/breaking schema comparisons.
- 26 unit/CLI tests and 117 fixture/vector/compatibility/retry/hash checks; isolated module and wheel verification documented in the PR.

### Limits

- Local conformance only: no service, payment executor, ledger, network adapter, database or model integration. Authentication, current-time freshness, financial transactions, state transitions and assembled outcomes remain owning services' responsibilities.
- Exact pinned readers reject undeclared fields; compatible optional changes are reported for reviewed schema evolution. Conservative comparisons may flag harmless schema rewrites for review.
- Baseline remains `sentinel.task-contracts.v1`, SHA-256 `0c728513e8b4ec0f34bcef63faa0207160d45cc7f20f872c1d9136ca7e252ffa`.
