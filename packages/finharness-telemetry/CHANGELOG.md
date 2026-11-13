# SN-024 changelog

## Unreleased

### Changed

- Redaction wraps `sentinel-telemetry` (path dep `../telemetry`): shared forbidden-key/value rejection; harness keep own allowlists.

### Added — 13 November 2026

- Independent module ownership, architecture/interface guide, scoped agent rules and acceptance checklist.
- `harness-telemetry.v1` library: `SafeHarnessHooks`, redaction, joined case/action/model/evaluation records, audit correlation, `run`/`CLI`, local exporter fakes.
- Local peer stubs for `telemetry.v1`, `finharness-runtime.v1`, and `finbench.v1` (valid/unavailable/malformed/unauthorized).
- Module-local `example/export-schema.json` and `example/grafana-dashboard.json`; `make check` / `make preview`.

### Implementation status

- Standalone fixture checks pass with in-process memory sinks and local stubs only.
- Real assembled peers remain UNVERIFIED until owner assembly. Fixture reports do not imply deployed runtime observations.
- Financial audit stays separate and unsampled; harness telemetry only correlates via redacted `audit.event_key` links.
