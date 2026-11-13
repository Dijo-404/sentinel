"""Narrow injected ports for telemetry export and separate financial audit."""

from __future__ import annotations

from typing import Protocol

from .contracts import CorrelationIds, FinancialAuditRecord, RecordedMetric, RecordedSpan


class SpanSink(Protocol):
    def export_span(self, span: RecordedSpan) -> None: ...


class MetricSink(Protocol):
    def export_metric(self, metric: RecordedMetric) -> None: ...


class TelemetryHooks(Protocol):
    """Injected hooks used by synthetic producers and future service adapters."""

    def start_span(
        self,
        name: str,
        correlation: CorrelationIds,
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


class FinancialAuditPort(Protocol):
    """Authoritative financial audit; telemetry must never sample or replace it."""

    def append(self, record: FinancialAuditRecord) -> None: ...
