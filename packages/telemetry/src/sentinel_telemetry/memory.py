"""In-process collector used by fixture checks and local preview."""

from __future__ import annotations

from dataclasses import dataclass, field

from .contracts import FinancialAuditRecord, RecordedMetric, RecordedSpan


@dataclass
class MemoryCollector:
    spans: list[RecordedSpan] = field(default_factory=list)
    metrics: list[RecordedMetric] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)

    def export_span(self, span: RecordedSpan) -> None:
        self.spans.append(span)

    def export_metric(self, metric: RecordedMetric) -> None:
        self.metrics.append(metric)

    def record_failure(self, reason: str) -> None:
        self.failures.append(reason)


@dataclass
class MemoryFinancialAudit:
    """Local double proving unsampled audit stays separate from telemetry."""

    records: list[FinancialAuditRecord] = field(default_factory=list)

    def append(self, record: FinancialAuditRecord) -> None:
        self.records.append(record)
