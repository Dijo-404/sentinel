"""Safe injected telemetry hooks: redact first; never break financial paths."""

from __future__ import annotations

from .contracts import CorrelationIds, RecordedMetric, RecordedSpan, RedactionError
from .memory import MemoryCollector
from .ports import MetricSink, SpanSink
from .redaction import (
    IDENTITY_VALUE_BOUNDED_METRIC_LABELS,
    sanitize_attributes,
    sanitize_metric_labels,
)


class FailingSink:
    """Deterministic exporter failure for isolation tests."""

    def export_span(self, span: RecordedSpan) -> None:
        raise RuntimeError("synthetic exporter failure")

    def export_metric(self, metric: RecordedMetric) -> None:
        raise RuntimeError("synthetic exporter failure")


class SafeTelemetryHooks:
    """
    Application-facing hooks.

    Redaction errors and sink failures are swallowed and counted. Callers continue;
    financial audit ports are never invoked from this type.
    """

    def __init__(
        self,
        span_sink: SpanSink,
        metric_sink: MetricSink,
        *,
        failure_log: MemoryCollector | None = None,
        service_name: str = "sentinel-telemetry",
        environment: str = "sandbox",
    ) -> None:
        self._spans = span_sink
        self._metrics = metric_sink
        self._failures = failure_log
        self._service_name = service_name
        self._environment = environment

    def _note_failure(self, reason: str) -> None:
        if self._failures is not None:
            self._failures.record_failure(reason)

    def start_span(
        self,
        name: str,
        correlation: CorrelationIds,
        attributes: dict[str, object] | None = None,
    ) -> RecordedSpan:
        try:
            merged = {
                "service.name": self._service_name,
                "deployment.environment": self._environment,
                **correlation.as_attributes(),
                **(attributes or {}),
            }
            cleaned = sanitize_attributes(merged)
            return RecordedSpan(name=name, attributes=cleaned, events=[])
        except (RedactionError, TypeError, ValueError) as exc:
            self._note_failure(f"start_span:{exc}")
            return RecordedSpan(name=name, attributes={}, events=[])

    def add_event(
        self,
        span: RecordedSpan,
        name: str,
        attributes: dict[str, object] | None = None,
    ) -> None:
        try:
            cleaned = sanitize_attributes(attributes)
            span.events.append({"name": name, "attributes": cleaned})
        except (RedactionError, TypeError, ValueError, AttributeError) as exc:
            self._note_failure(f"add_event:{exc}")

    def end_span(self, span: RecordedSpan) -> None:
        try:
            self._spans.export_span(span)
        except Exception as exc:  # noqa: BLE001 — telemetry must not raise into callers
            self._note_failure(f"end_span:{exc}")

    def record_metric(
        self,
        name: str,
        value: float,
        labels: dict[str, object] | None = None,
    ) -> None:
        try:
            if not isinstance(name, str) or not name or len(name) > 128:
                raise RedactionError("Metric name invalid")
            # Identity value-bounded keys must go through identity sanitize.
            if labels and IDENTITY_VALUE_BOUNDED_METRIC_LABELS.intersection(labels):
                from .identity import sanitize_identity_metric_labels

                cleaned = sanitize_identity_metric_labels(labels)
            else:
                cleaned = sanitize_metric_labels(labels)
            metric = RecordedMetric(name=name, value=float(value), labels=cleaned)
            self._metrics.export_metric(metric)
        except Exception as exc:  # noqa: BLE001
            self._note_failure(f"record_metric:{exc}")
