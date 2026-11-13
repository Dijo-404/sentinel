"""In-package fixture peers for standalone checks. Not deployed evidence."""

from __future__ import annotations

from typing import Any

from .contracts import CONTRACT_VERSION, RecordedMetric, RecordedSpan
from .memory import MemoryCollector


class FixtureTelemetryExporter:
    """Local telemetry.v1 emitter fake. evidence_mode remains fixture."""

    def __init__(self, collector: MemoryCollector | None = None) -> None:
        self.collector = collector or MemoryCollector()

    def export_span(self, span: RecordedSpan) -> None:
        self.collector.export_span(span)

    def export_metric(self, metric: RecordedMetric) -> None:
        self.collector.export_metric(metric)


class FixtureRuntime:
    """Local finharness-runtime.v1 observation fake."""

    def observe_case(self, case_id: str) -> dict[str, Any]:
        return {
            "contract_version": CONTRACT_VERSION,
            "case_id": case_id,
            "action_id": "action-demo-1",
            "model_version": "demo-model-v1",
            "runtime_version": "finharness-runtime-v1",
            "mode": "fixture",
            "evidence_mode": "fixture",
        }


class FixtureFinbench:
    """Local finbench.v1 evaluation observation fake."""

    def observe_evaluation(self, suite_id: str) -> dict[str, Any]:
        return {
            "contract_version": CONTRACT_VERSION,
            "suite_id": suite_id,
            "evaluation_version": "finbench-eval-v1",
            "dataset_version": "finbench-indic-demo-v1",
            "hard_safety_pass": True,
            "mode": "fixture",
            "evidence_mode": "fixture",
        }
