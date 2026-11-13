"""Harness redaction: wraps sentinel_telemetry.redaction with harness allowlists."""

from __future__ import annotations

from collections.abc import Mapping

from sentinel_telemetry.contracts import RedactionError as TelemetryRedactionError
from sentinel_telemetry.redaction import (
    FORBIDDEN_KEY_FRAGMENTS,
    normalize_key,
)
from sentinel_telemetry.redaction import (
    reject_value as telemetry_reject_value,
)

from .contracts import RedactionError

CORRELATION_ATTRIBUTE_KEYS = frozenset(
    {
        "request_id",
        "case_id",
        "action_id",
        "model.version",
        "evaluation.version",
        "runtime.version",
        "dataset.version",
        "audit.event_key",
        "service.name",
        "deployment.environment",
        "workflow.version",
        "policy.version",
        "error.type",
        "event.kind",
        "action.type",
        "candidate.version",
        "scenario.family",
        "parse.result",
        "payment.result_category",
    }
)

ALLOWED_METRIC_LABELS = frozenset(
    {
        "service",
        "environment",
        "outcome",
        "scenario",
        "tool",
        "action_type",
        "provider",
        "error_type",
        "model_class",
        "suite",
        "event_kind",
    }
)

_FORBIDDEN_METRIC_ONLY = frozenset(
    {
        "case_id",
        "request_id",
        "action_id",
        "model.version",
        "evaluation.version",
        "runtime.version",
        "dataset.version",
        "audit.event_key",
        "transaction_ref",
        "order_reference",
        "subject_ref",
        "customer_id",
    }
)


def _reject_key(key: str, *, for_metric: bool) -> None:
    if not isinstance(key, str) or not key or len(key) > 64:
        raise RedactionError("Telemetry key must be a nonempty string up to 64 characters")
    normalized = normalize_key(key)
    if for_metric and (
        normalized in {normalize_key(k) for k in _FORBIDDEN_METRIC_ONLY}
        or normalized in {normalize_key(k) for k in CORRELATION_ATTRIBUTE_KEYS}
    ):
        raise RedactionError("Correlation and customer-payment identifiers are not metric labels")
    for fragment in FORBIDDEN_KEY_FRAGMENTS:
        if fragment in normalized:
            raise RedactionError("Forbidden telemetry key rejected")


def _reject_value(value: object) -> str | int | bool:
    try:
        return telemetry_reject_value(value)
    except TelemetryRedactionError as exc:
        raise RedactionError(str(exc)) from None


def sanitize_attributes(attributes: Mapping[str, object] | None) -> dict[str, str | int | bool]:
    """Allowlisted correlation/operational span attributes; reject secrets and raw text."""
    if attributes is None:
        return {}
    if not isinstance(attributes, Mapping):
        raise RedactionError("Attributes must be a mapping")
    cleaned: dict[str, str | int | bool] = {}
    allow_norm = {normalize_key(k) for k in CORRELATION_ATTRIBUTE_KEYS}
    for key, value in attributes.items():
        _reject_key(key, for_metric=False)
        if key not in CORRELATION_ATTRIBUTE_KEYS and normalize_key(key) not in allow_norm:
            raise RedactionError("Attribute key is not on the harness telemetry allowlist")
        cleaned[key if key in CORRELATION_ATTRIBUTE_KEYS else key] = _reject_value(value)
    return cleaned


def sanitize_metric_labels(labels: Mapping[str, object] | None) -> dict[str, str]:
    """Bounded Prometheus-style labels; never correlation or payment identifiers."""
    if labels is None:
        return {}
    if not isinstance(labels, Mapping):
        raise RedactionError("Metric labels must be a mapping")
    if len(labels) > 8:
        raise RedactionError("Metric label cardinality bound exceeded")
    cleaned: dict[str, str] = {}
    for key, value in labels.items():
        _reject_key(key, for_metric=True)
        if key not in ALLOWED_METRIC_LABELS:
            raise RedactionError("Metric label is not on the bounded allowlist")
        sanitized = _reject_value(value)
        if not isinstance(sanitized, str):
            raise RedactionError("Metric label values must be strings")
        if len(sanitized) > 64:
            raise RedactionError("Metric label value exceeds bound")
        cleaned[key] = sanitized
    return cleaned
