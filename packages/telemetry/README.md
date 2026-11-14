# SN-015 / SN-042 — Standalone telemetry package

`telemetry.v1` injected OpenTelemetry hooks, allowlisted redaction, bounded-label metrics, and a module-local collector/dashboard example. Synthetic producers exercise request/approval/worker/provider correlation plus timeout and retry-suppression events. SN-042 adds identity span/metric helpers and a gated admin observability projection (docs/roles.md §15).

**Owned root:** `packages/telemetry/` · **Branches:** `feat/sn-015-observability`, `feat/sn-042-identity-observability`

Contract: `sentinel.task-contracts.v1`, SHA-256 `0db3ba2bba994f10d3060bc7173035360c15ffe23189cea409f7327e23c36feb`. Local typed snapshot: [contracts.py](src/sentinel_telemetry/contracts.py), [telemetry.v1.json](contracts/telemetry.v1.json), [fixtures](fixtures/).

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
    emit_session_authenticate,
    produce_correlated_journey,
    project_admin_observability_health,
    sanitize_attributes,
    sanitize_metric_labels,
    run,
)

collector = MemoryCollector()
hooks = SafeTelemetryHooks(collector, collector, failure_log=collector)
audit = MemoryFinancialAudit()
produce_correlated_journey(hooks, audit)
emit_session_authenticate(hooks, request_id="req-login-1", role="operator", result="success")
health = project_admin_observability_health()  # live_stats is always None
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
- Metric labels: bounded allowlist (`service`, `environment`, `outcome`, `scenario`, `tool`, `action_type`, `provider`, `error_type`, `queue`, `event_kind`). Identity keys `role` / `result` / `operation` / `permission` / `reason` are **not** free-form via `sanitize_metric_labels` — use `sanitize_identity_metric_labels` or `emit_*` helpers (bounded values only). `environment` for identity metrics is `sandbox` / `fixture` / `prod` / `unknown`. Correlation IDs and PII are never labels.
- `SafeTelemetryHooks` swallows redaction/exporter failures so callers continue. It never writes financial audit or identity audit.
- `mode: real-peers` returns `UNVERIFIED` until an assembled collector is wired; there is no silent fixture fallback.

## Identity helpers (SN-042)

Helpers in [`identity.py`](src/sentinel_telemetry/identity.py) name spans and metrics from roles.md §15:

| Span | Metric |
|---|---|
| `identity.session.authenticate` | `identity_login_attempts_total{role,result}` |
| `identity.staff.invite` | `identity_staff_invitations_total{result}` |
| `identity.role.assign` / `identity.role.revoke` | `identity_role_changes_total{role,operation}` |
| `identity.session.revoke` | `identity_session_revocation_latency_seconds` |
| (metric only) | `identity_authz_denied_total{permission,reason}` |

**Financial audit ≠ identity audit ≠ telemetry.** Action-ledger financial audit stays unsampled and authoritative for money. Identity audit events (`identity_audit_events`) stay authoritative inside identity.v1. Telemetry export failure must never suppress either audit family. Do not put emails, user IDs, tokens, or invitation secrets in metric labels.

Permission label values follow §9.1 dotted catalog IDs (e.g. `financial.approval.decide`, `identity.staff.invite`). Free-form `sanitize_metric_labels({"role": ...})` is rejected; call `sanitize_identity_metric_labels` or the emit helpers.

### Identity service adoption (optional path dep)

`services/identity` does not yet depend on this package (no shared root lockfile). When identity adopts helpers, add a module-local path dependency only:

```toml
# services/identity/pyproject.toml (example — not applied by SN-042)
dependencies = [
  # ...existing...
  "sentinel-telemetry",
]
[tool.uv.sources]
sentinel-telemetry = { path = "../../packages/telemetry" }
```

Then call `emit_session_authenticate` / `emit_staff_invite` / `emit_role_change` / `emit_session_revoke` / `emit_authz_denied` from HTTP adapters after domain success/failure. Keep domain free of OTel imports.

### Gated admin eval surface

`project_admin_observability_health()` returns a redacted projection for `/admin/observability` and `/admin/evaluations`. FinHarness and FinBench stay `gated_disabled` (or `shadow_read_only_unavailable` if flags are set). `live_stats` is always `None` — no fake live rates. SN-042 does **not** claim FinHarness/FinBench complete (roles.md M5/M8).

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
- [x] Identity §15 span/metric helpers with bounded labels; admin health projection gated (no live stats).
- [x] `make -C packages/telemetry check` with module-local uv lock only.
- [ ] Assembled real OTLP collector/Grafana/Tempo against product services (owner assembly).
- [ ] Identity service path-dep + live emission on login/invite (optional follow-up).
- [ ] FinHarness/FinBench admin eval wiring (M5/M8; independently gated — not SN-042 complete).

Evidence mode for standalone checks: fixture / synthetic producers. No payment simulator, live model, or sibling service is required or contacted.
