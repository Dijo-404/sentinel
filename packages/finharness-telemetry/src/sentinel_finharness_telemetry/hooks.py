"""Safe injected harness hooks: redact first; never break financial paths."""

from __future__ import annotations

from .contracts import (
    AuditCorrelationRecord,
    HarnessCorrelation,
    MissingExporterError,
    RecordedMetric,
    RecordedSpan,
    RedactionError,
)
from .memory import MemoryCollector
from .ports import MetricSink, SpanSink
from .redaction import sanitize_attributes, sanitize_metric_labels


class SafeHarnessHooks:
    """
    Application-facing harness telemetry hooks.

    Redaction errors and sink failures are swallowed and counted. Callers continue;
    financial audit ports are never invoked from this type. Audit correlation links
    are telemetry-side only and never replace an unsampled audit write.
    """

    def __init__(
        self,
        span_sink: SpanSink | None,
        metric_sink: MetricSink | None,
        *,
        failure_log: MemoryCollector | None = None,
        service_name: str = "sentinel-finharness-telemetry",
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
        correlation: HarnessCorrelation,
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
        if self._spans is None:
            self._note_failure("end_span:MissingExporterError:base telemetry exporter missing")
            return
        try:
            self._spans.export_span(span)
        except MissingExporterError as exc:
            self._note_failure(f"end_span:MissingExporterError:{exc}")
        except Exception as exc:  # noqa: BLE001 — telemetry must not raise into callers
            self._note_failure(f"end_span:{type(exc).__name__}:{exc}")

    def record_metric(
        self,
        name: str,
        value: float,
        labels: dict[str, object] | None = None,
    ) -> None:
        if self._metrics is None:
            self._note_failure("record_metric:MissingExporterError:base telemetry exporter missing")
            return
        try:
            if not isinstance(name, str) or not name or len(name) > 128:
                raise RedactionError("Metric name invalid")
            cleaned = sanitize_metric_labels(labels)
            metric = RecordedMetric(name=name, value=float(value), labels=cleaned)
            self._metrics.export_metric(metric)
        except Exception as exc:  # noqa: BLE001
            self._note_failure(f"record_metric:{exc}")

    def correlate_audit(self, record: AuditCorrelationRecord) -> None:
        """Record a redacted telemetry-side link; does not write financial audit."""
        try:
            sanitize_attributes(
                {
                    "audit.event_key": record.audit_event_key,
                    "action_id": record.action_id,
                    "case_id": record.case_id,
                    "request_id": record.request_id,
                }
            )
            if self._failures is not None:
                self._failures.record_audit_link(record)
        except (RedactionError, TypeError, ValueError) as exc:
            self._note_failure(f"correlate_audit:{exc}")
