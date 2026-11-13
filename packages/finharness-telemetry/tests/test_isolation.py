"""Telemetry outage and missing exporter must not suppress financial audit."""

from sentinel_finharness_telemetry import (
    FailingExporter,
    MemoryCollector,
    MemoryFinancialAudit,
    MissingExporter,
    SafeHarnessHooks,
    produce_with_failing_telemetry,
)


def test_failing_exporter_still_records_financial_audit() -> None:
    failures = MemoryCollector()
    hooks = SafeHarnessHooks(FailingExporter(), FailingExporter(), failure_log=failures)
    audit = MemoryFinancialAudit()
    produce_with_failing_telemetry(hooks, audit)

    assert len(audit.records) == 1
    assert audit.records[0].outcome == "OUTCOME_UNKNOWN"
    assert audit.records[0].event_key == "audit-demo-failover-1"
    assert len(failures.failures) >= 1
    assert failures.spans == []
    assert failures.metrics == []


def test_missing_exporter_fails_safely_and_keeps_audit() -> None:
    failures = MemoryCollector()
    hooks = SafeHarnessHooks(None, None, failure_log=failures)
    audit = MemoryFinancialAudit()
    produce_with_failing_telemetry(hooks, audit)

    assert len(audit.records) == 1
    assert any("missing" in reason.lower() for reason in failures.failures)


def test_missing_exporter_object_fails_safely() -> None:
    failures = MemoryCollector()
    hooks = SafeHarnessHooks(MissingExporter(), MissingExporter(), failure_log=failures)
    audit = MemoryFinancialAudit()
    produce_with_failing_telemetry(hooks, audit)

    assert len(audit.records) == 1
    assert any("MissingExporterError" in reason for reason in failures.failures)


def test_safe_hooks_swallow_redacted_metric_without_raising() -> None:
    collector = MemoryCollector()
    hooks = SafeHarnessHooks(collector, collector, failure_log=collector)
    hooks.record_metric(
        "finharness_bad",
        1.0,
        {"case_id": "case-demo-42", "action_id": "action-demo-1"},
    )
    assert collector.metrics == []
    assert collector.failures
