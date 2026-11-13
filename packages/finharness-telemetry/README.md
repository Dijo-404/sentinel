# SN-024 — Standalone harness telemetry extension

`harness-telemetry.v1` injectable sanitized runtime/evaluation hooks, audit correlation, and module-local dashboard/export examples. Local emitter/exporter fakes only — does not modify `packages/telemetry` or import sibling implementations.

**Owned root:** `packages/finharness-telemetry/` · **Branch:** `feat/sn-024-harness-observability`

Contract: `sentinel.task-contracts.v1`, SHA-256 `0c728513e8b4ec0f34bcef63faa0207160d45cc7f20f872c1d9136ca7e252ffa`. Local typed snapshot: [contracts.py](src/sentinel_finharness_telemetry/contracts.py), [harness-telemetry.v1.json](contracts/harness-telemetry.v1.json), [fixtures](fixtures/).

## Standalone setup and checks

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/). No database, Docker, sibling packages, or running Sentinel peers.

```sh
make setup
make check
```

Or from the repository root:

```sh
make -C packages/finharness-telemetry check
```

`uv sync --frozen` installs only this module's locked dependencies. `make check` runs Ruff lint/format and pytest. Fixture mode uses in-process memory sinks and local peer doubles under [tests/stubs/](tests/stubs/).

Preview the `RunReport`:

```sh
make preview
# or
uv run --frozen sentinel-finharness-telemetry preview
```

## Public surface

```python
from sentinel_finharness_telemetry import (
    SafeHarnessHooks,
    MemoryCollector,
    MemoryFinancialAudit,
    produce_harness_journey,
    sanitize_attributes,
    sanitize_metric_labels,
    run,
)

collector = MemoryCollector()
hooks = SafeHarnessHooks(collector, collector, failure_log=collector)
audit = MemoryFinancialAudit()
produce_harness_journey(hooks, audit)
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

- Span/event attributes join `case_id`, `action_id`, `model.version`, and `evaluation.version` (plus optional runtime/dataset/audit keys). Secrets, raw complaints, prompts, and customer/payment identifiers are rejected.
- Metric labels: bounded allowlist (`service`, `environment`, `outcome`, `scenario`, `tool`, `action_type`, `provider`, `error_type`, `model_class`, `suite`, `event_kind`). Correlation and version IDs are never labels.
- `SafeHarnessHooks` swallows redaction/exporter/outage/missing-exporter failures so callers continue. It never writes financial audit; `correlate_audit` is a telemetry-side link only.
- Financial audit remains a separate unsampled port (`MemoryFinancialAudit` / ledger-owned in assembly).
- Fixture `RunReport` artifacts always use `evidence_mode: fixture` and set `deployed_runtime_observations: false`. They never imply deployed evidence.
- `mode: real-peers` rejects missing/malformed/unauthorized peers and returns `FAIL`/`UNVERIFIED` with no silent fixture fallback.

## Consumed local peer doubles

Under [tests/stubs/](tests/stubs/):

| Port | Cases |
| --- | --- |
| `telemetry.v1` | valid, unavailable, malformed, unauthorized_or_out_of_scope |
| `finharness-runtime.v1` | valid, unavailable, malformed, unauthorized_or_out_of_scope |
| `finbench.v1` | valid, unavailable, malformed, unauthorized_or_out_of_scope |

Real-peer adapters live in [adapters.py](src/sentinel_finharness_telemetry/adapters.py).

## Example export and dashboard

Static examples under [example/](example/):

- `export-schema.json` — joined-version export shape and forbidden metric labels
- `grafana-dashboard.json` — panels for harness cases, model requests, FinBench score, and audit correlation note

These files are hashed into fixture `RunReport` artifacts. `make check` does not start Collector or Grafana.

## Compatibility checklist and evidence

- [x] Task-local typed `RunInput`/`RunReport` and harness correlation snapshot; pinned contract hash recorded.
- [x] Injected sanitized runtime/evaluation hooks via local emitter/exporter fakes; no sibling telemetry package edits.
- [x] Joined case/action/model/evaluation versions on bounded redacted records; audit correlation without sampling financial audit.
- [x] Telemetry outage, missing base exporter, and malformed input fail safely.
- [x] Fixture reports labeled `evidence_mode=fixture`; never imply deployed runtime observations.
- [x] Stub cases for `telemetry.v1`, `finharness-runtime.v1`, `finbench.v1`.
- [x] `make -C packages/finharness-telemetry check` with module-local uv lock only.
- [ ] Assembled real telemetry exporter / FinHarness runtime / FinBench peers (owner assembly).

Evidence mode for standalone checks: fixture / synthetic producers. No payment simulator, live model, or sibling service is required or contacted.
