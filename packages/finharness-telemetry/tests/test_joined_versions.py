"""Hooks join case/action/model/evaluation versions without sampling audit."""

from stubs.finbench import ValidFinbench
from stubs.finharness_runtime import ValidRuntime

from sentinel_finharness_telemetry import (
    MemoryCollector,
    MemoryFinancialAudit,
    SafeHarnessHooks,
    produce_harness_journey,
)
from sentinel_finharness_telemetry.adapters import RealFinbenchAdapter, RealRuntimeAdapter


def test_producers_join_versions_and_keep_audit_unsampled() -> None:
    collector = MemoryCollector()
    hooks = SafeHarnessHooks(collector, collector, failure_log=collector)
    audit = MemoryFinancialAudit()
    runtime = RealRuntimeAdapter(ValidRuntime())
    finbench = RealFinbenchAdapter(ValidFinbench())

    result = produce_harness_journey(hooks, audit, runtime=runtime, finbench=finbench)
    correlation = result["correlation"]

    assert correlation.case_id == "case-demo-42"
    assert correlation.action_id == "action-demo-1"
    assert correlation.model_version == "demo-model-v1"
    assert correlation.evaluation_version == "finbench-eval-v1"

    names = {span.name for span in collector.spans}
    assert names == {
        "finharness.model.propose",
        "finharness.case.verify",
        "finbench.scenario.run",
    }
    for span in collector.spans:
        assert span.attributes["case_id"] == "case-demo-42"
        assert span.attributes["action_id"] == "action-demo-1"
        assert span.attributes["model.version"] == "demo-model-v1"
        assert span.attributes["evaluation.version"] == "finbench-eval-v1"

    assert len(audit.records) == 1
    assert audit.records[0].event_key == "audit-demo-1"
    assert len(collector.audit_links) == 1
    assert collector.audit_links[0].audit_event_key == "audit-demo-1"
