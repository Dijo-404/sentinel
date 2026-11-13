"""telemetry.v1 stub cases: valid, unavailable, malformed, unauthorized_or_out_of_scope."""

from __future__ import annotations

from sentinel_finharness_telemetry.contracts import PeerError, RecordedMetric, RecordedSpan
from sentinel_finharness_telemetry.memory import MemoryCollector


class ValidTelemetryExporter:
    def __init__(self, collector: MemoryCollector | None = None) -> None:
        self.collector = collector or MemoryCollector()

    def export_span(self, span: RecordedSpan) -> None:
        self.collector.export_span(span)

    def export_metric(self, metric: RecordedMetric) -> None:
        self.collector.export_metric(metric)


class UnavailableTelemetry:
    def export_span(self, span: RecordedSpan) -> None:
        raise PeerError("telemetry.v1", "unavailable", "telemetry exporter unreachable")

    def export_metric(self, metric: RecordedMetric) -> None:
        raise PeerError("telemetry.v1", "unavailable", "telemetry exporter unreachable")


class MalformedTelemetry:
    """Accepts calls but records nothing useful; adapter treats empty peer state as malformed."""

    def export_span(self, span: RecordedSpan) -> None:
        _ = span
        # Malformed: pretend success while dropping required export semantics.
        return None

    def export_metric(self, metric: RecordedMetric) -> None:
        _ = metric
        return None

    def capabilities(self) -> dict:
        return {"mode": "broken"}


class UnauthorizedTelemetry:
    def export_span(self, span: RecordedSpan) -> None:
        raise PeerError(
            "telemetry.v1",
            "unauthorized_or_out_of_scope",
            "tenant scope denied for exporter",
        )

    def export_metric(self, metric: RecordedMetric) -> None:
        raise PeerError(
            "telemetry.v1",
            "unauthorized_or_out_of_scope",
            "tenant scope denied for exporter",
        )
