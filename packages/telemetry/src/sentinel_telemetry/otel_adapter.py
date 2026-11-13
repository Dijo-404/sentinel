"""OpenTelemetry-backed sink wrapping the SDK; optional for fixture memory path."""

from __future__ import annotations

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from .contracts import RecordedMetric, RecordedSpan
from .memory import MemoryCollector


class OTelMemoryBridge:
    """
    Dual-write sink: records sanitized module spans and mirrors them into OTel SDK
    in-memory exporter so local checks prove injected OTel hooks work.
    """

    def __init__(
        self,
        collector: MemoryCollector,
        service_name: str = "sentinel-telemetry",
    ) -> None:
        self._collector = collector
        self._exporter = InMemorySpanExporter()
        provider = TracerProvider(
            resource=Resource.create({"service.name": service_name}),
        )
        provider.add_span_processor(SimpleSpanProcessor(self._exporter))
        self._tracer = provider.get_tracer("sentinel.telemetry.v1")
        self._provider = provider

    @property
    def otel_spans(self):
        return self._exporter.get_finished_spans()

    def export_span(self, span: RecordedSpan) -> None:
        with self._tracer.start_as_current_span(span.name) as otel_span:
            for key, value in span.attributes.items():
                otel_span.set_attribute(key, value)
            for event in span.events:
                otel_span.add_event(event["name"], attributes=dict(event.get("attributes") or {}))
        self._collector.export_span(span)

    def export_metric(self, metric: RecordedMetric) -> None:
        # Metrics stay module-local; OTel metrics SDK is optional for this package slice.
        self._collector.export_metric(metric)

    def shutdown(self) -> None:
        self._provider.shutdown()


def force_tracer() -> trace.Tracer:
    """Expose a tracer for callers that inject their own provider."""
    return trace.get_tracer("sentinel.telemetry.v1")
