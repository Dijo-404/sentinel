"""telemetry.v1 RunInput → RunReport entry point."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .contracts import (
    COMPONENT_VERSION,
    CONTRACT_SHA256,
    CONTRACT_VERSION,
    PORT,
    ArtifactRef,
    CheckResult,
    RedactionError,
    RunInput,
    RunReport,
    TelemetryContractError,
)
from .hooks import FailingSink, SafeTelemetryHooks
from .memory import MemoryCollector, MemoryFinancialAudit
from .otel_adapter import OTelMemoryBridge
from .producers import produce_correlated_journey, produce_with_failing_telemetry
from .redaction import sanitize_attributes, sanitize_metric_labels

SUPPORTED_PARAMETERS = frozenset(
    {
        "telemetry.service_name",
        "telemetry.environment",
        "telemetry.require_otel_spans",
    }
)


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _package_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _check(
    name: str,
    ok: bool,
    pass_code: str,
    fail_code: str,
) -> CheckResult:
    return CheckResult(
        name=name,
        status="PASS" if ok else "FAIL",
        reason_code=pass_code if ok else fail_code,
    )


def run(input_data: RunInput | dict) -> RunReport:
    if isinstance(input_data, dict):
        parsed = RunInput.from_dict(input_data)
    else:
        parsed = input_data

    unknown = set(parsed.parameters) - SUPPORTED_PARAMETERS
    if unknown:
        raise TelemetryContractError(f"Unsupported required parameter: {sorted(unknown)[0]}")

    service_name = str(parsed.parameters.get("telemetry.service_name", "sentinel-telemetry"))
    environment = str(parsed.parameters.get("telemetry.environment", "sandbox"))
    require_otel = bool(parsed.parameters.get("telemetry.require_otel_spans", True))

    checks: list[CheckResult] = []
    output_artifacts: list[ArtifactRef] = []

    if parsed.mode == "real-peers":
        checks.append(
            CheckResult(
                name="real_peer_collector",
                status="UNVERIFIED",
                reason_code="REAL_PEER_COLLECTOR_NOT_ASSEMBLED",
            )
        )
        return RunReport(
            contract_version="sentinel.task-contracts.v1",
            run_id=parsed.run_id,
            mode=parsed.mode,
            status="UNVERIFIED",
            checks=checks,
            output_artifacts=[],
        )

    collector = MemoryCollector()
    bridge = OTelMemoryBridge(collector, service_name=service_name)
    hooks = SafeTelemetryHooks(
        bridge,
        bridge,
        failure_log=collector,
        service_name=service_name,
        environment=environment,
    )
    audit = MemoryFinancialAudit()
    try:
        produce_correlated_journey(hooks, audit)
        otel_count = len(bridge.otel_spans)
    finally:
        bridge.shutdown()

    span_names = {span.name for span in collector.spans}
    correlation_ok = all(
        span.attributes.get("request_id") == "request-demo-1"
        and span.attributes.get("approval_id") == "approval-demo-1"
        and span.attributes.get("worker_id") == "worker-demo-1"
        and span.attributes.get("provider_ref") == "refund-demo-1"
        for span in collector.spans
    ) and span_names >= {
        "case.request",
        "approval.decide",
        "workflow.dispatch",
        "provider.refund.apply",
    }
    checks.append(_check("correlation_export", correlation_ok, "CORRELATED", "CORRELATION_MISSING"))

    event_kinds = {
        event["attributes"].get("event.kind") for span in collector.spans for event in span.events
    }
    events_ok = {"timeout", "retry_suppression", "request", "approval", "worker"} <= event_kinds
    checks.append(_check("timeout_retry_events", events_ok, "EVENTS_PRESENT", "EVENTS_MISSING"))

    otel_ok = (not require_otel) or otel_count >= 4
    checks.append(_check("otel_hooks", otel_ok, "OTEL_SPANS_RECORDED", "OTEL_SPANS_MISSING"))

    redaction_ok = True
    for attrs in (
        {"authorization": "Bearer sk-secret-token-value0123"},
        {"case_id": "case-demo-42", "complaint": "I was charged twice"},
        {"case_id": "case-demo-42", "message": "please refund my order"},
    ):
        try:
            sanitize_attributes(attrs)
            redaction_ok = False
        except RedactionError:
            pass
    for labels in (
        {"case_id": "case-demo-42"},
        {"transaction_ref": "TXN-B"},
        {"customer_id": "cust-1"},
        {"order_reference": "DEMO-ORDER-42"},
    ):
        try:
            sanitize_metric_labels(labels)
            redaction_ok = False
        except RedactionError:
            pass
    try:
        sanitize_attributes(
            {
                "case_id": "case-demo-42",
                "request_id": "request-demo-1",
                "approval_id": "approval-demo-1",
                "worker_id": "worker-demo-1",
                "provider_ref": "refund-demo-1",
            }
        )
    except RedactionError:
        redaction_ok = False
    checks.append(_check("redaction_bounds", redaction_ok, "REDACTION_OK", "REDACTION_FAILED"))

    fail_collector = MemoryCollector()
    failing = FailingSink()
    fail_hooks = SafeTelemetryHooks(
        failing,
        failing,
        failure_log=fail_collector,
        service_name=service_name,
        environment=environment,
    )
    fail_audit = MemoryFinancialAudit()
    produce_with_failing_telemetry(fail_hooks, fail_audit)
    isolation_ok = (
        len(fail_audit.records) == 1
        and fail_audit.records[0].outcome == "OUTCOME_UNKNOWN"
        and len(fail_collector.failures) >= 1
        and len(audit.records) == 1
    )
    checks.append(_check("audit_isolation", isolation_ok, "AUDIT_UNSAMPLED", "AUDIT_SUPPRESSED"))

    export_payload = {
        "contract_version": CONTRACT_VERSION,
        "port": PORT,
        "baseline_sha256": CONTRACT_SHA256,
        "run_id": parsed.run_id,
        "spans": [
            {"name": s.name, "attributes": dict(s.attributes), "events": list(s.events)}
            for s in collector.spans
        ],
        "metrics": [
            {"name": m.name, "value": m.value, "labels": dict(m.labels)} for m in collector.metrics
        ],
        "financial_audit_separate": [
            {
                "event_key": a.event_key,
                "action_id": a.action_id,
                "outcome": a.outcome,
            }
            for a in audit.records
        ],
    }
    export_text = json.dumps(export_payload, sort_keys=True, separators=(",", ":"))
    output_artifacts.append(
        ArtifactRef(
            kind="telemetry-export",
            uri="fixture://telemetry-export",
            sha256=_sha256_text(export_text),
            component_version=COMPONENT_VERSION,
            evidence_mode="fixture",
        )
    )

    example_dir = _package_root() / "example"
    for name, kind in (
        ("otel-collector.yaml", "collector-example"),
        ("grafana-dashboard.json", "dashboard-example"),
    ):
        path = example_dir / name
        if path.is_file():
            output_artifacts.append(
                ArtifactRef(
                    kind=kind,
                    uri=str(path.relative_to(_package_root())),
                    sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                    component_version=COMPONENT_VERSION,
                    evidence_mode="fixture",
                )
            )

    status = "PASS" if all(c.status == "PASS" for c in checks) else "FAIL"
    return RunReport(
        contract_version="sentinel.task-contracts.v1",
        run_id=parsed.run_id,
        mode=parsed.mode,
        status=status,
        checks=checks,
        output_artifacts=output_artifacts,
    )
