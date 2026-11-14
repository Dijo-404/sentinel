# SN-015 / SN-042 changelog

## Unreleased

### Changed (finding #13)

- `mode: real-peers` exports correlated spans to a configured collector
  (`telemetry.collector_endpoint` or `OTEL_EXPORTER_OTLP_ENDPOINT`).
- Export success → `PASS` / `COLLECTOR_EXPORT_OK` with `evidence_mode: real-component`.
- Export failure → `FAIL` / `COLLECTOR_EXPORT_FAILED` (no fixture promotion).
- Missing endpoint still `UNVERIFIED` / `REAL_PEER_COLLECTOR_NOT_ASSEMBLED`.

### Added (SN-042)

- Identity span/metric helpers (`identity.session.authenticate`, invite, role assign/revoke, session revoke) and §15.2 metric names with bounded labels.
- `sanitize_identity_metric_labels` for `role` / `result` / `operation` / `permission` / `reason` (dotted §9.1 permission IDs; free-form `sanitize_metric_labels` rejects those keys).
- Identity `environment` bounded to `sandbox` / `fixture` / `prod` / `unknown`.
- `project_admin_observability_health()` gated admin projection; FinHarness/FinBench disabled by default; `live_stats` always `None`.
- Docs: financial audit ≠ identity audit ≠ sampled telemetry; optional identity path-dep adoption notes.

### Changed

- Export `FORBIDDEN_KEY_FRAGMENTS`, `normalize_key`, and `reject_value` for finharness-telemetry reuse.

### Added (SN-015)

- `sentinel-telemetry` package implementing `telemetry.v1`: injected OTel hooks, allowlisted redaction, bounded-label metrics, synthetic correlation producers, and module-local collector/dashboard examples.
- `make check` runs Ruff and pytest; fixture `run()` proves correlation, timeout/retry-suppression events, redaction rejection, and financial-audit isolation.
- CLI: `sentinel-telemetry check|preview|run` with explicit `UNVERIFIED` when no collector endpoint is configured.

### Implementation status

- Fixture evidence + real-peers HTTP export path (PASS only on successful collector response).
- Full OTLP protobuf Collector/Grafana/Tempo against product services remains owner-assembled.
- FinHarness/FinBench admin eval surfaces remain independently gated; SN-042 does not claim them complete.
- Identity service emission not wired in this change (README adoption path only).
