"""In-process collector and audit doubles used by fixture checks."""

from __future__ import annotations

from dataclasses import dataclass, field

from .contracts import (
    AuditCorrelationRecord,
    FinancialAuditRecord,
    MissingExporterError,
    RecordedMetric,
    RecordedSpan,
)


@dataclass
class MemoryCollector:
    spans: list[RecordedSpan] = field(default_factory=list)
    metrics: list[RecordedMetric] = field(default_factory=list)
    audit_links: list[AuditCorrelationRecord] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)

    def export_span(self, span: RecordedSpan) -> None:
        self.spans.append(span)

    def export_metric(self, metric: RecordedMetric) -> None:
        self.metrics.append(metric)

    def record_failure(self, reason: str) -> None:
        self.failures.append(reason)

    def record_audit_link(self, record: AuditCorrelationRecord) -> None:
        self.audit_links.append(record)


@dataclass
class MemoryFinancialAudit:
    """Local double proving unsampled audit stays separate from telemetry."""

    records: list[FinancialAuditRecord] = field(default_factory=list)

    def append(self, record: FinancialAuditRecord) -> None:
        self.records.append(record)


class MissingExporter:
    """Deterministic missing base exporter for isolation tests."""

    def export_span(self, span: RecordedSpan) -> None:
        raise MissingExporterError("base telemetry exporter not configured")

    def export_metric(self, metric: RecordedMetric) -> None:
        raise MissingExporterError("base telemetry exporter not configured")


class FailingExporter:
    """Deterministic exporter outage for isolation tests."""

    def export_span(self, span: RecordedSpan) -> None:
        raise RuntimeError("synthetic telemetry outage")

    def export_metric(self, metric: RecordedMetric) -> None:
        raise RuntimeError("synthetic telemetry outage")
