"""Narrow injected ports for harness telemetry and separate financial audit."""

from __future__ import annotations

from typing import Any, Protocol

from .contracts import (
    AuditCorrelationRecord,
    FinancialAuditRecord,
    HarnessCorrelation,
    RecordedMetric,
    RecordedSpan,
)


class SpanSink(Protocol):
    def export_span(self, span: RecordedSpan) -> None: ...


class MetricSink(Protocol):
    def export_metric(self, metric: RecordedMetric) -> None: ...


class BaseTelemetryExporter(Protocol):
    """Local fake or injected telemetry.v1 exporter. Never import sibling packages."""

    def export_span(self, span: RecordedSpan) -> None: ...

    def export_metric(self, metric: RecordedMetric) -> None: ...


class RuntimeObservationPort(Protocol):
    """finharness-runtime.v1 observation double."""

    def observe_case(self, case_id: str) -> dict[str, Any]: ...


class FinbenchObservationPort(Protocol):
    """finbench.v1 evaluation observation double."""

    def observe_evaluation(self, suite_id: str) -> dict[str, Any]: ...


class FinancialAuditPort(Protocol):
    """Authoritative financial audit; telemetry must never sample or replace it."""

    def append(self, record: FinancialAuditRecord) -> None: ...


class HarnessTelemetryHooks(Protocol):
    def start_span(
        self,
        name: str,
        correlation: HarnessCorrelation,
        attributes: dict[str, object] | None = None,
    ) -> RecordedSpan: ...

    def add_event(
        self,
        span: RecordedSpan,
        name: str,
        attributes: dict[str, object] | None = None,
    ) -> None: ...

    def end_span(self, span: RecordedSpan) -> None: ...

    def record_metric(
        self,
        name: str,
        value: float,
        labels: dict[str, object] | None = None,
    ) -> None: ...

    def correlate_audit(self, record: AuditCorrelationRecord) -> None: ...
