"""Framework-free redaction and bounded-label rules for harness-telemetry.v1."""

from __future__ import annotations

import re
from collections.abc import Mapping

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

_FORBIDDEN_KEY_FRAGMENTS = (
    "password",
    "secret",
    "token",
    "authorization",
    "api_key",
    "apikey",
    "otp",
    "cvv",
    "pan",
    "upi_pin",
    "pin",
    "complaint",
    "prompt",
    "message",
    "raw_",
    "customer",
    "subject_ref",
    "transaction_ref",
    "order_reference",
    "card",
    "audio",
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

_SECRET_VALUE = re.compile(
    r"(?i)(bearer\s+[a-z0-9\-._~+/]+=*|sk-[a-z0-9]{16,}|"
    r"\b\d{12,19}\b|"
    r"\b\d{4,8}\b.*otp|upi[_\s-]?pin)",
)
_RAW_COMPLAINT = re.compile(r"(?i)(i was charged twice|please refund|my card ending)")


def _normalize_key(key: str) -> str:
    return key.strip().lower().replace("-", "_")


def _reject_key(key: str, *, for_metric: bool) -> None:
    if not isinstance(key, str) or not key or len(key) > 64:
        raise RedactionError("Telemetry key must be a nonempty string up to 64 characters")
    normalized = _normalize_key(key)
    if for_metric and (
        normalized in {_normalize_key(k) for k in _FORBIDDEN_METRIC_ONLY}
        or normalized in {_normalize_key(k) for k in CORRELATION_ATTRIBUTE_KEYS}
    ):
        raise RedactionError("Correlation and customer-payment identifiers are not metric labels")
    for fragment in _FORBIDDEN_KEY_FRAGMENTS:
        if fragment in normalized:
            raise RedactionError("Forbidden telemetry key rejected")


def _reject_value(value: object) -> str | int | bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if not isinstance(value, str):
        raise RedactionError("Telemetry values must be string, int, or bool")
    if len(value) > 256:
        raise RedactionError("Telemetry string value exceeds bound")
    if _SECRET_VALUE.search(value) or _RAW_COMPLAINT.search(value):
        raise RedactionError("Secret, raw complaint, or payment identifier value rejected")
    return value


def sanitize_attributes(attributes: Mapping[str, object] | None) -> dict[str, str | int | bool]:
    """Allowlisted correlation/operational span attributes; reject secrets and raw text."""
    if attributes is None:
        return {}
    if not isinstance(attributes, Mapping):
        raise RedactionError("Attributes must be a mapping")
    cleaned: dict[str, str | int | bool] = {}
    allow_norm = {_normalize_key(k) for k in CORRELATION_ATTRIBUTE_KEYS}
    for key, value in attributes.items():
        _reject_key(key, for_metric=False)
        if key not in CORRELATION_ATTRIBUTE_KEYS and _normalize_key(key) not in allow_norm:
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
