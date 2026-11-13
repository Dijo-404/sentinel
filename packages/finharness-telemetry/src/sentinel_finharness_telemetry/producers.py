"""Local synthetic harness producers; no sibling package imports."""

from __future__ import annotations

from typing import Any

from .contracts import AuditCorrelationRecord, FinancialAuditRecord, HarnessCorrelation
from .ports import (
    FinancialAuditPort,
    FinbenchObservationPort,
    HarnessTelemetryHooks,
    RuntimeObservationPort,
)

DEMO_CORRELATION = HarnessCorrelation(
    request_id="request-demo-1",
    case_id="case-demo-42",
    action_id="action-demo-1",
    model_version="demo-model-v1",
    evaluation_version="finbench-eval-v1",
    runtime_version="finharness-runtime-v1",
    dataset_version="finbench-indic-demo-v1",
    audit_event_key="audit-demo-1",
)


def produce_harness_journey(
    hooks: HarnessTelemetryHooks,
    audit: FinancialAuditPort,
    *,
    runtime: RuntimeObservationPort | None = None,
    finbench: FinbenchObservationPort | None = None,
    correlation: HarnessCorrelation = DEMO_CORRELATION,
) -> dict[str, Any]:
    """
    Emit runtime + evaluation spans joined by case/action/model/evaluation versions.
    Financial audit is written separately and is never sampled or replaced by telemetry.
    """
    runtime_obs: dict[str, Any] = {}
    if runtime is not None:
        runtime_obs = dict(runtime.observe_case(correlation.case_id))
        correlation = HarnessCorrelation(
            request_id=correlation.request_id,
            case_id=correlation.case_id,
            action_id=str(runtime_obs.get("action_id", correlation.action_id)),
            model_version=str(runtime_obs.get("model_version", correlation.model_version)),
            evaluation_version=correlation.evaluation_version,
            runtime_version=str(runtime_obs.get("runtime_version", correlation.runtime_version)),
            dataset_version=correlation.dataset_version,
            audit_event_key=correlation.audit_event_key,
        )

    eval_obs: dict[str, Any] = {}
    if finbench is not None:
        eval_obs = dict(finbench.observe_evaluation("finbench-indic-demo"))
        correlation = HarnessCorrelation(
            request_id=correlation.request_id,
            case_id=correlation.case_id,
            action_id=correlation.action_id,
            model_version=correlation.model_version,
            evaluation_version=str(
                eval_obs.get("evaluation_version", correlation.evaluation_version)
            ),
            runtime_version=correlation.runtime_version,
            dataset_version=str(eval_obs.get("dataset_version", correlation.dataset_version)),
            audit_event_key=correlation.audit_event_key,
        )

    model = hooks.start_span(
        "finharness.model.propose",
        correlation,
        {
            "action.type": "REQUEST_REFUND",
            "parse.result": "ok",
            "candidate.version": "champion-c1",
        },
    )
    hooks.add_event(model, "model.proposal", {"event.kind": "proposal"})
    hooks.end_span(model)
    hooks.record_metric(
        "finharness_model_requests_total",
        1.0,
        {
            "service": "finharness-runtime",
            "environment": "sandbox",
            "model_class": "structured",
            "outcome": "ok",
        },
    )

    runtime_span = hooks.start_span(
        "finharness.case.verify",
        correlation,
        {"action.type": "REQUEST_REFUND", "workflow.version": "demo-workflow-v1"},
    )
    hooks.add_event(runtime_span, "runtime.shadow_compare", {"event.kind": "runtime"})
    hooks.end_span(runtime_span)
    hooks.record_metric(
        "finharness_cases_total",
        1.0,
        {
            "service": "finharness-runtime",
            "environment": "sandbox",
            "scenario": "duplicate_payment",
            "outcome": "verified",
        },
    )

    eval_span = hooks.start_span(
        "finbench.scenario.run",
        correlation,
        {
            "scenario.family": "duplicate_payment",
            "candidate.version": "champion-c1",
        },
    )
    hooks.add_event(eval_span, "evaluation.scored", {"event.kind": "evaluation"})
    hooks.end_span(eval_span)
    hooks.record_metric(
        "finbench_score",
        1.0,
        {
            "service": "finbench",
            "environment": "sandbox",
            "suite": "indic-demo",
            "outcome": "pass",
        },
    )

    audit.append(
        FinancialAuditRecord(
            event_key=correlation.audit_event_key or "audit-demo-1",
            action_id=correlation.action_id,
            outcome="OUTCOME_UNKNOWN",
        )
    )
    hooks.correlate_audit(
        AuditCorrelationRecord(
            audit_event_key=correlation.audit_event_key or "audit-demo-1",
            action_id=correlation.action_id,
            case_id=correlation.case_id,
            request_id=correlation.request_id,
        )
    )
    return {
        "correlation": correlation,
        "runtime": runtime_obs,
        "evaluation": eval_obs,
    }


def produce_with_failing_telemetry(
    hooks: HarnessTelemetryHooks,
    audit: FinancialAuditPort,
    *,
    correlation: HarnessCorrelation = DEMO_CORRELATION,
) -> None:
    """Same financial audit path while telemetry sink may be failing or missing."""
    span = hooks.start_span(
        "finharness.action.submit",
        correlation,
        {"action.type": "REQUEST_REFUND"},
    )
    hooks.add_event(span, "provider.timeout", {"event.kind": "timeout", "error.type": "timeout"})
    hooks.end_span(span)
    hooks.record_metric(
        "finharness_actions_total",
        1.0,
        {
            "service": "finharness-runtime",
            "environment": "sandbox",
            "action_type": "REQUEST_REFUND",
            "outcome": "timeout",
        },
    )
    audit.append(
        FinancialAuditRecord(
            event_key="audit-demo-failover-1",
            action_id=correlation.action_id,
            outcome="OUTCOME_UNKNOWN",
        )
    )
    hooks.correlate_audit(
        AuditCorrelationRecord(
            audit_event_key="audit-demo-failover-1",
            action_id=correlation.action_id,
            case_id=correlation.case_id,
            request_id=correlation.request_id,
        )
    )
