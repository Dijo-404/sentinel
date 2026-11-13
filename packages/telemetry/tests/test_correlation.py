"""Local producers export request/approval/worker/provider correlation."""

from sentinel_telemetry import (
    MemoryCollector,
    MemoryFinancialAudit,
    SafeTelemetryHooks,
    produce_correlated_journey,
)
from sentinel_telemetry.otel_adapter import OTelMemoryBridge


def test_producers_export_correlation_and_timeout_retry_events() -> None:
    collector = MemoryCollector()
    bridge = OTelMemoryBridge(collector)
    hooks = SafeTelemetryHooks(bridge, bridge, failure_log=collector)
    audit = MemoryFinancialAudit()
    try:
        produce_correlated_journey(hooks, audit)
        otel_names = {span.name for span in bridge.otel_spans}
    finally:
        bridge.shutdown()

    names = {span.name for span in collector.spans}
    assert names == {
        "case.request",
        "approval.decide",
        "workflow.dispatch",
        "provider.refund.apply",
    }
    for span in collector.spans:
        assert span.attributes["request_id"] == "request-demo-1"
        assert span.attributes["approval_id"] == "approval-demo-1"
        assert span.attributes["worker_id"] == "worker-demo-1"
        assert span.attributes["provider_ref"] == "refund-demo-1"
        assert span.attributes["case_id"] == "case-demo-42"

    kinds = {event["attributes"]["event.kind"] for span in collector.spans for event in span.events}
    assert "timeout" in kinds
    assert "retry_suppression" in kinds
    assert otel_names >= names
    assert len(audit.records) == 1
    assert any(m.name == "sentinel_retry_suppressed_total" for m in collector.metrics)
