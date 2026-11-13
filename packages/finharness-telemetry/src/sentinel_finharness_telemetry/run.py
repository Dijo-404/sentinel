"""harness-telemetry.v1 RunInput → RunReport entry point."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .adapters import RealFinbenchAdapter, RealRuntimeAdapter, RealTelemetryExporterAdapter
from .contracts import (
    COMPONENT_VERSION,
    CONTRACT_SHA256,
    CONTRACT_VERSION,
    PORT,
    ArtifactRef,
    CheckResult,
    HarnessTelemetryContractError,
    PeerError,
    RedactionError,
    RunInput,
    RunReport,
)
from .hooks import SafeHarnessHooks
from .memory import FailingExporter, MemoryCollector, MemoryFinancialAudit, MissingExporter
from .producers import produce_harness_journey, produce_with_failing_telemetry
from .redaction import sanitize_attributes, sanitize_metric_labels

SUPPORTED_PARAMETERS = frozenset(
    {
        "harness_telemetry.service_name",
        "harness_telemetry.environment",
        "harness_telemetry.require_joined_versions",
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


def run(
    input_data: RunInput | dict,
    *,
    telemetry_peer: object | None = None,
    runtime_peer: object | None = None,
    finbench_peer: object | None = None,
) -> RunReport:
    if isinstance(input_data, dict):
        parsed = RunInput.from_dict(input_data)
    else:
        parsed = input_data

    unknown = set(parsed.parameters) - SUPPORTED_PARAMETERS
    if unknown:
        raise HarnessTelemetryContractError(f"Unsupported required parameter: {sorted(unknown)[0]}")

    service_name = str(
        parsed.parameters.get("harness_telemetry.service_name", "sentinel-finharness-telemetry")
    )
    environment = str(parsed.parameters.get("harness_telemetry.environment", "sandbox"))
    require_joined = bool(parsed.parameters.get("harness_telemetry.require_joined_versions", True))

    checks: list[CheckResult] = []
    output_artifacts: list[ArtifactRef] = []

    if parsed.mode == "real-peers":
        # Real-peer mode never silently falls back to fixture success.
        peer_checks: list[CheckResult] = []
        try:
            if telemetry_peer is None:
                raise PeerError("telemetry.v1", "unavailable", "exporter peer not assembled")
            RealTelemetryExporterAdapter(telemetry_peer)
            peer_checks.append(
                CheckResult(
                    name="telemetry_peer",
                    status="UNVERIFIED",
                    reason_code="REAL_PEER_TELEMETRY_NOT_ASSEMBLED",
                )
            )
        except PeerError as exc:
            peer_checks.append(
                CheckResult(name="telemetry_peer", status="FAIL", reason_code=exc.kind.upper())
            )
        try:
            if runtime_peer is None:
                raise PeerError("finharness-runtime.v1", "unavailable", "runtime peer missing")
            RealRuntimeAdapter(runtime_peer).observe_case("case-demo-42")
            peer_checks.append(
                CheckResult(name="runtime_peer", status="PASS", reason_code="RUNTIME_PEER_OK")
            )
        except PeerError as exc:
            peer_checks.append(
                CheckResult(name="runtime_peer", status="FAIL", reason_code=exc.kind.upper())
            )
        try:
            if finbench_peer is None:
                raise PeerError("finbench.v1", "unavailable", "finbench peer missing")
            RealFinbenchAdapter(finbench_peer).observe_evaluation("finbench-indic-demo")
            peer_checks.append(
                CheckResult(name="finbench_peer", status="PASS", reason_code="FINBENCH_PEER_OK")
            )
        except PeerError as exc:
            peer_checks.append(
                CheckResult(name="finbench_peer", status="FAIL", reason_code=exc.kind.upper())
            )

        if any(c.status == "FAIL" for c in peer_checks):
            status: str = "FAIL"
        elif any(c.status == "UNVERIFIED" for c in peer_checks):
            status = "UNVERIFIED"
        else:
            status = "PASS"
        return RunReport(
            contract_version="sentinel.task-contracts.v1",
            run_id=parsed.run_id,
            mode=parsed.mode,
            status=status,  # type: ignore[arg-type]
            checks=peer_checks,
            output_artifacts=[],
        )

    # Fixture mode: local emitter/exporter fakes only. Never claim deployed evidence.
    collector = MemoryCollector()
    hooks = SafeHarnessHooks(
        collector,
        collector,
        failure_log=collector,
        service_name=service_name,
        environment=environment,
    )
    audit = MemoryFinancialAudit()

    # Local fixture peers only (in-process fakes, not sibling packages).
    from .local_peers import FixtureFinbench, FixtureRuntime, FixtureTelemetryExporter

    runtime = RealRuntimeAdapter(FixtureRuntime())
    finbench = RealFinbenchAdapter(FixtureFinbench())
    _ = RealTelemetryExporterAdapter(FixtureTelemetryExporter(collector))

    result = produce_harness_journey(hooks, audit, runtime=runtime, finbench=finbench)
    correlation = result["correlation"]

    joined_ok = (
        correlation.case_id == "case-demo-42"
        and correlation.action_id == "action-demo-1"
        and correlation.model_version == "demo-model-v1"
        and correlation.evaluation_version == "finbench-eval-v1"
        and all(
            span.attributes.get("case_id") == "case-demo-42"
            and span.attributes.get("action_id") == "action-demo-1"
            and span.attributes.get("model.version") == "demo-model-v1"
            and span.attributes.get("evaluation.version") == "finbench-eval-v1"
            for span in collector.spans
        )
    )
    if require_joined:
        checks.append(_check("joined_versions", joined_ok, "VERSIONS_JOINED", "VERSIONS_MISSING"))
    else:
        checks.append(CheckResult(name="joined_versions", status="PASS", reason_code="SKIPPED"))

    span_names = {span.name for span in collector.spans}
    spans_ok = span_names >= {
        "finharness.model.propose",
        "finharness.case.verify",
        "finbench.scenario.run",
    }
    checks.append(_check("harness_spans", spans_ok, "SPANS_PRESENT", "SPANS_MISSING"))

    audit_ok = (
        len(audit.records) == 1
        and audit.records[0].event_key == "audit-demo-1"
        and len(collector.audit_links) == 1
        and collector.audit_links[0].audit_event_key == "audit-demo-1"
    )
    checks.append(_check("audit_correlation", audit_ok, "AUDIT_LINKED", "AUDIT_LINK_MISSING"))

    redaction_ok = True
    for attrs in (
        {"authorization": "Bearer sk-secret-token-value0123"},
        {"case_id": "case-demo-42", "complaint": "I was charged twice"},
        {"case_id": "case-demo-42", "prompt": "refund please"},
    ):
        try:
            sanitize_attributes(attrs)
            redaction_ok = False
        except RedactionError:
            pass
    for labels in (
        {"case_id": "case-demo-42"},
        {"action_id": "action-demo-1"},
        {"model.version": "demo-model-v1"},
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
                "action_id": "action-demo-1",
                "model.version": "demo-model-v1",
                "evaluation.version": "finbench-eval-v1",
                "request_id": "request-demo-1",
            }
        )
    except RedactionError:
        redaction_ok = False
    checks.append(_check("redaction_bounds", redaction_ok, "REDACTION_OK", "REDACTION_FAILED"))

    # Telemetry outage must not suppress financial audit.
    fail_collector = MemoryCollector()
    fail_hooks = SafeHarnessHooks(
        FailingExporter(),
        FailingExporter(),
        failure_log=fail_collector,
        service_name=service_name,
        environment=environment,
    )
    fail_audit = MemoryFinancialAudit()
    produce_with_failing_telemetry(fail_hooks, fail_audit)
    outage_ok = (
        len(fail_audit.records) == 1
        and fail_audit.records[0].outcome == "OUTCOME_UNKNOWN"
        and len(fail_collector.failures) >= 1
    )
    checks.append(_check("telemetry_outage", outage_ok, "OUTAGE_SAFE", "OUTAGE_UNSAFE"))

    # Missing base exporter fails safely; audit still written.
    missing_collector = MemoryCollector()
    missing_hooks = SafeHarnessHooks(
        None,
        None,
        failure_log=missing_collector,
        service_name=service_name,
        environment=environment,
    )
    # Also exercise MissingExporter sink object.
    missing_sink_hooks = SafeHarnessHooks(
        MissingExporter(),
        MissingExporter(),
        failure_log=missing_collector,
        service_name=service_name,
        environment=environment,
    )
    missing_audit = MemoryFinancialAudit()
    produce_with_failing_telemetry(missing_hooks, missing_audit)
    produce_with_failing_telemetry(missing_sink_hooks, missing_audit)
    missing_ok = len(missing_audit.records) == 2 and any(
        "MissingExporterError" in f or "missing" in f for f in missing_collector.failures
    )
    checks.append(
        _check("missing_exporter", missing_ok, "MISSING_EXPORTER_SAFE", "MISSING_EXPORTER_UNSAFE")
    )

    export_payload = {
        "contract_version": CONTRACT_VERSION,
        "port": PORT,
        "baseline_sha256": CONTRACT_SHA256,
        "run_id": parsed.run_id,
        "evidence_mode": "fixture",
        "deployed_runtime_observations": False,
        "spans": [
            {"name": s.name, "attributes": dict(s.attributes), "events": list(s.events)}
            for s in collector.spans
        ],
        "metrics": [
            {"name": m.name, "value": m.value, "labels": dict(m.labels)} for m in collector.metrics
        ],
        "audit_correlation": [
            {
                "audit_event_key": link.audit_event_key,
                "action_id": link.action_id,
                "case_id": link.case_id,
                "request_id": link.request_id,
            }
            for link in collector.audit_links
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
            kind="harness-telemetry-export",
            uri="fixture://harness-telemetry-export",
            sha256=_sha256_text(export_text),
            component_version=COMPONENT_VERSION,
            evidence_mode="fixture",
        )
    )

    example_dir = _package_root() / "example"
    for name, kind in (
        ("export-schema.json", "export-example"),
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

    # Fixture reports must never claim deployed evidence.
    evidence_label_ok = all(a.evidence_mode == "fixture" for a in output_artifacts)
    checks.append(
        _check(
            "fixture_evidence_label",
            evidence_label_ok,
            "FIXTURE_LABELED",
            "DEPLOYED_EVIDENCE_CLAIMED",
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
