"""HTTP export to a configured OTLP/collector endpoint for real-peers runs."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from collections.abc import Callable
from typing import Any

from .contracts import RecordedMetric, RecordedSpan

UrlOpen = Callable[..., Any]


class CollectorExportError(RuntimeError):
    """Export failed; real-peers must fail closed (no fixture promotion)."""


def resolve_collector_endpoint(parameters: dict[str, Any]) -> str | None:
    """Prefer RunInput parameter, then OTEL_EXPORTER_OTLP_ENDPOINT."""
    raw = parameters.get("telemetry.collector_endpoint")
    if raw is None or raw == "":
        raw = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT") or os.environ.get(
            "TELEMETRY_COLLECTOR_ENDPOINT"
        )
    if raw is None or str(raw).strip() == "":
        return None
    return str(raw).rstrip("/")


def _traces_url(endpoint: str) -> str:
    if endpoint.endswith("/v1/traces"):
        return endpoint
    return f"{endpoint}/v1/traces"


def export_spans_to_collector(
    endpoint: str,
    spans: list[RecordedSpan],
    metrics: list[RecordedMetric],
    *,
    run_id: str,
    service_name: str,
    timeout_s: float = 5.0,
    opener: UrlOpen | None = None,
) -> str:
    """
    POST a JSON span batch to the collector.

    Accepts 2xx. Any transport/HTTP failure raises CollectorExportError.
    Payload is labeled for Sentinel module checks; full OTLP protobuf remains
    owner-assembled against the example collector.
    """
    url = _traces_url(endpoint)
    body = {
        "resourceSpans": [
            {
                "resource": {
                    "attributes": [
                        {"key": "service.name", "value": {"stringValue": service_name}},
                        {"key": "sentinel.run_id", "value": {"stringValue": run_id}},
                    ]
                },
                "scopeSpans": [
                    {
                        "spans": [
                            {
                                "name": span.name,
                                "attributes": [
                                    {"key": k, "value": {"stringValue": str(v)}}
                                    for k, v in span.attributes.items()
                                ],
                                "events": [
                                    {
                                        "name": event["name"],
                                        "attributes": [
                                            {
                                                "key": ek,
                                                "value": {"stringValue": str(ev)},
                                            }
                                            for ek, ev in (event.get("attributes") or {}).items()
                                        ],
                                    }
                                    for event in span.events
                                ],
                            }
                            for span in spans
                        ]
                    }
                ],
            }
        ],
        "sentinel_metrics": [
            {"name": m.name, "value": m.value, "labels": dict(m.labels)} for m in metrics
        ],
    }
    payload = json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    open_fn = opener or urllib.request.urlopen
    try:
        with open_fn(request, timeout=timeout_s) as response:
            status = getattr(response, "status", None) or response.getcode()
            if int(status) < 200 or int(status) >= 300:
                raise CollectorExportError(f"collector returned HTTP {status}")
            return url
    except CollectorExportError:
        raise
    except urllib.error.HTTPError as exc:
        raise CollectorExportError(f"collector HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise CollectorExportError(f"collector unreachable: {exc.reason}") from exc
    except OSError as exc:
        raise CollectorExportError(f"collector export failed: {exc}") from exc
