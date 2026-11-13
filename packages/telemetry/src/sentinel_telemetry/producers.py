"""Local synthetic span/event producers; no API/worker service imports."""

from __future__ import annotations

from .contracts import CorrelationIds, FinancialAuditRecord
from .ports import FinancialAuditPort, TelemetryHooks

DEMO_CORRELATION = CorrelationIds(
    request_id="request-demo-1",
    case_id="case-demo-42",
    approval_id="approval-demo-1",
    worker_id="worker-demo-1",
    provider_ref="refund-demo-1",
    action_id="action-demo-1",
    workflow_run_id="workflow-run-demo-1",
)


def produce_correlated_journey(
    hooks: TelemetryHooks,
    audit: FinancialAuditPort,
    *,
    correlation: CorrelationIds = DEMO_CORRELATION,
) -> None:
    """
    Emit request → approval → worker → provider spans with shared correlation,
    plus timeout and retry-suppression events. Financial audit is written separately
    and is never sampled or replaced by telemetry.
    """
    request = hooks.start_span(
        "case.request",
        correlation,
        {"action.type": "REQUEST_REFUND", "workflow.version": "demo-workflow-v1"},
    )
    hooks.add_event(request, "request.accepted", {"event.kind": "request"})
    hooks.end_span(request)
    hooks.record_metric(
        "sentinel_cases_started_total",
        1.0,
        {"service": "case-api", "environment": "sandbox", "scenario": "duplicate_payment"},
    )

    approval = hooks.start_span(
        "approval.decide",
        correlation,
        {"action.type": "REQUEST_REFUND", "policy.version": "demo-policy-v1"},
    )
    hooks.add_event(approval, "approval.granted", {"event.kind": "approval"})
    hooks.end_span(approval)
    hooks.record_metric(
        "sentinel_actions_total",
        1.0,
        {
            "service": "action-ledger",
            "environment": "sandbox",
            "action_type": "REQUEST_REFUND",
            "outcome": "approved",
        },
    )

    worker = hooks.start_span(
        "workflow.dispatch",
        correlation,
        {"action.type": "REQUEST_REFUND"},
    )
    hooks.add_event(worker, "worker.claimed", {"event.kind": "worker"})
    hooks.end_span(worker)

    provider = hooks.start_span(
        "provider.refund.apply",
        correlation,
        {"payment.provider": "simulator", "action.type": "REQUEST_REFUND"},
    )
    hooks.add_event(
        provider,
        "provider.timeout",
        {"event.kind": "timeout", "error.type": "timeout", "payment.result_category": "unknown"},
    )
    hooks.add_event(
        provider,
        "provider.retry_suppressed",
        {"event.kind": "retry_suppression", "error.type": "ambiguous_outcome"},
    )
    hooks.end_span(provider)
    hooks.record_metric(
        "sentinel_tool_calls_total",
        1.0,
        {
            "service": "dispatcher",
            "environment": "sandbox",
            "tool": "refund.apply",
            "provider": "simulator",
            "outcome": "timeout",
            "error_type": "timeout",
        },
    )
    hooks.record_metric(
        "sentinel_retry_suppressed_total",
        1.0,
        {
            "service": "dispatcher",
            "environment": "sandbox",
            "tool": "refund.apply",
            "provider": "simulator",
            "event_kind": "retry_suppression",
            "outcome": "suppressed",
        },
    )

    # Unsampled financial audit: written regardless of telemetry exporter health.
    audit.append(
        FinancialAuditRecord(
            event_key="audit-demo-1",
            action_id=correlation.action_id or "action-demo-1",
            outcome="OUTCOME_UNKNOWN",
        )
    )


def produce_with_failing_telemetry(
    hooks: TelemetryHooks,
    audit: FinancialAuditPort,
    *,
    correlation: CorrelationIds = DEMO_CORRELATION,
) -> None:
    """Same financial audit path while telemetry sink may be failing."""
    span = hooks.start_span("provider.refund.apply", correlation, {"payment.provider": "simulator"})
    hooks.add_event(span, "provider.timeout", {"event.kind": "timeout", "error.type": "timeout"})
    hooks.end_span(span)
    hooks.record_metric(
        "sentinel_tool_calls_total",
        1.0,
        {"service": "dispatcher", "environment": "sandbox", "outcome": "timeout"},
    )
    audit.append(
        FinancialAuditRecord(
            event_key="audit-demo-failover-1",
            action_id=correlation.action_id or "action-demo-1",
            outcome="OUTCOME_UNKNOWN",
        )
    )
