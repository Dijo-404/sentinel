# SN-015 — Standalone telemetry package

`telemetry.v1` injected OpenTelemetry hooks, allowlisted redaction, bounded-label metrics, and a module-local collector/dashboard example. Synthetic producers exercise request/approval/worker/provider correlation plus timeout and retry-suppression events. Financial audit remains a separate unsampled port.

**Owned root:** `packages/telemetry/` · **Branch:** `feat/sn-015-observability`

Contract: `sentinel.task-contracts.v1`, SHA-256 `0c728513e8b4ec0f34bcef63faa0207160d45cc7f20f872c1d9136ca7e252ffa`. Local typed snapshot: [contracts.py](src/sentinel_telemetry/contracts.py), [telemetry.v1.json](contracts/telemetry.v1.json), [fixtures](fixtures/).

## Standalone setup and checks

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/). No database, Docker, sibling packages, or running Sentinel peers.

```sh
make setup
make check
```

Or from the repository root:

```sh
make -C packages/telemetry check
```

`uv sync --frozen` installs only this module's locked dependencies. `make check` runs Ruff lint/format and pytest. Fixture mode uses an in-process OTel `InMemorySpanExporter` and memory sinks.

Preview the `RunReport`:

```sh
make preview
# or
uv run --frozen sentinel-telemetry preview
```

## Public surface

```python
from sentinel_telemetry import (
    SafeTelemetryHooks,
    MemoryCollector,
    MemoryFinancialAudit,
    produce_correlated_journey,
    sanitize_attributes,
    sanitize_metric_labels,
    run,
)

collector = MemoryCollector()
hooks = SafeTelemetryHooks(collector, collector, failure_log=collector)
audit = MemoryFinancialAudit()
produce_correlated_journey(hooks, audit)
report = run(
    {
        "contract_version": "sentinel.task-contracts.v1",
        "run_id": "local-1",
        "mode": "fixture",
        "input_artifacts": [],
        "parameters": {},
    }
)
```

- Span/event attributes: allowlisted correlation and operational keys only. Secrets, raw complaints, prompts, and customer/payment identifiers are rejected.
- Metric labels: bounded allowlist (`service`, `environment`, `outcome`, `scenario`, `tool`, `action_type`, `provider`, `error_type`, `queue`, `event_kind`). Correlation IDs are never labels.
- `SafeTelemetryHooks` swallows redaction/exporter failures so callers continue. It never writes financial audit.
- `mode: real-peers` returns `UNVERIFIED` until an assembled collector is wired; there is no silent fixture fallback.

## Example collector and dashboard

Static examples under [example/](example/):

- `otel-collector.yaml` — local OTLP receiver with delete actions for forbidden keys
- `grafana-dashboard.json` — panels for case starts, timeouts, retry suppression, and a Tempo correlation note

These files are hashed into fixture `RunReport` artifacts. `make check` does not start Collector or Grafana.

## Compatibility checklist and evidence

- [x] Task-local typed `RunInput`/`RunReport` and correlation snapshot; pinned contract hash recorded.
- [x] Injected OTel hooks via SDK in-memory exporter; synthetic producers only.
- [x] Correlation across request/approval/worker/provider; timeout and retry-suppression events.
- [x] Redaction/bounded-label rejection for secrets, raw complaints, customer/payment identifiers.
- [x] Failing exporter still records separate financial audit; hooks never replace audit.
- [x] `make -C packages/telemetry check` with module-local uv lock only.
- [ ] Assembled real OTLP collector/Grafana/Tempo against product services (owner assembly).

Evidence mode for standalone checks: fixture / synthetic producers. No payment simulator, live model, or sibling service is required or contacted.
