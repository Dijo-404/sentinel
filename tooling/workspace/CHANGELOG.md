# SN-001 changelog

## Unreleased

### Changed — 15 November 2026

- Applied the repository Ruff baseline to module discovery, bounded check execution, and tests without changing check behavior.

### Added — 13 November 2026

- Installable standard-library `sentinel-modules` CLI with module-local manifest,
  lockfile, configuration example, `make check`, and fixture preview.
- `module-checks.v1` typed snapshot and pinned baseline hash; discovery reports
  READY, ABSENT and UNIMPLEMENTED separately from executed check results.
- Optional per-module and changed-path selection, including deleted/renamed and
  extra owned paths, without global dependency installation.
- Strict declaration/path validation and fixed argv-based check execution;
  visible failures, bounded captured output, per-check timeout and child cleanup
  preserve unrelated check progress without fixture fallback.
- Independent miniature repositories and 16 acceptance/negative tests; no
  sibling source, services, database, payment provider or model required.
- Pinned-action, read-only, provider-secret-free CI with standalone tooling
  installation, discovery reporting and changed-module checks for PRs.

### Validation and limits

- Local tests exercise real Make subprocesses against synthetic fixtures.
- Optional aggregation assumes modules own their setup/check commands; it does
  not install sibling dependencies, sandbox trusted Makefiles, or prove product
  assembly/release readiness. ABSENT/UNIMPLEMENTED/SKIPPED never mean PASS.
