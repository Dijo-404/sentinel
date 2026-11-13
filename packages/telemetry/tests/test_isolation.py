"""Telemetry failures must not suppress or replace financial audit."""

from sentinel_telemetry import (
    FailingSink,
    MemoryCollector,
    MemoryFinancialAudit,
    SafeTelemetryHooks,
    produce_with_failing_telemetry,
)


def test_failing_exporter_still_records_financial_audit() -> None:
    failures = MemoryCollector()
    hooks = SafeTelemetryHooks(FailingSink(), FailingSink(), failure_log=failures)
    audit = MemoryFinancialAudit()
    produce_with_failing_telemetry(hooks, audit)

    assert len(audit.records) == 1
    assert audit.records[0].outcome == "OUTCOME_UNKNOWN"
    assert audit.records[0].event_key == "audit-demo-failover-1"
    assert len(failures.failures) >= 1
    assert failures.spans == []
    assert failures.metrics == []


def test_safe_hooks_swallow_redacted_metric_without_raising() -> None:
    collector = MemoryCollector()
    hooks = SafeTelemetryHooks(collector, collector, failure_log=collector)
    hooks.record_metric(
        "sentinel_bad",
        1.0,
        {"case_id": "case-demo-42", "transaction_ref": "TXN-B"},
    )
    assert collector.metrics == []
    assert collector.failures
