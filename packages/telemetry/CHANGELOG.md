# SN-015 changelog

## Unreleased

### Added

- `sentinel-telemetry` package implementing `telemetry.v1`: injected OTel hooks, allowlisted redaction, bounded-label metrics, synthetic correlation producers, and module-local collector/dashboard examples.
- `make check` runs Ruff and pytest; fixture `run()` proves correlation, timeout/retry-suppression events, redaction rejection, and financial-audit isolation.
- CLI: `sentinel-telemetry check|preview|run` with explicit `UNVERIFIED` real-peers status when no assembled collector is present.

### Implementation status

- Standalone fixture evidence only. Real-peer Collector/Grafana assembly remains owner-verified and separate from this module check.
