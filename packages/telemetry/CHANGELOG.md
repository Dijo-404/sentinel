# SN-015 / SN-042 changelog

## Unreleased

### Added (SN-042)

- Identity span/metric helpers (`identity.session.authenticate`, invite, role assign/revoke, session revoke) and §15.2 metric names with bounded labels.
- Metric label allowlist extended with `role`, `result`, `operation`, `permission`, `reason` (no PII).
- `project_admin_observability_health()` gated admin projection; FinHarness/FinBench disabled by default; `live_stats` always `None`.
- Docs: financial audit ≠ identity audit ≠ sampled telemetry; optional identity path-dep adoption notes.

### Changed

- Export `FORBIDDEN_KEY_FRAGMENTS`, `normalize_key`, and `reject_value` for finharness-telemetry reuse.

### Added (SN-015)

- `sentinel-telemetry` package implementing `telemetry.v1`: injected OTel hooks, allowlisted redaction, bounded-label metrics, synthetic correlation producers, and module-local collector/dashboard examples.
- `make check` runs Ruff and pytest; fixture `run()` proves correlation, timeout/retry-suppression events, redaction rejection, and financial-audit isolation.
- CLI: `sentinel-telemetry check|preview|run` with explicit `UNVERIFIED` real-peers status when no assembled collector is present.

### Implementation status

- Standalone fixture evidence only. Real-peer Collector/Grafana assembly remains owner-verified and separate from this module check.
- FinHarness/FinBench admin eval surfaces remain independently gated; SN-042 does not claim them complete.
- Identity service emission not wired in this change (README adoption path only).
