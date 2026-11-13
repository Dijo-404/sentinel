"""Bounded redaction rejects secrets and correlation-as-metric-labels."""

import pytest

from sentinel_finharness_telemetry import (
    RedactionError,
    sanitize_attributes,
    sanitize_metric_labels,
)


def test_allows_joined_version_attributes() -> None:
    cleaned = sanitize_attributes(
        {
            "case_id": "case-demo-42",
            "action_id": "action-demo-1",
            "model.version": "demo-model-v1",
            "evaluation.version": "finbench-eval-v1",
            "request_id": "request-demo-1",
        }
    )
    assert cleaned["model.version"] == "demo-model-v1"
    assert cleaned["evaluation.version"] == "finbench-eval-v1"


@pytest.mark.parametrize(
    "attrs",
    [
        {"authorization": "Bearer sk-secret-token-value0123"},
        {"case_id": "case-demo-42", "complaint": "I was charged twice"},
        {"prompt": "please refund"},
    ],
)
def test_rejects_forbidden_attributes(attrs: dict) -> None:
    with pytest.raises(RedactionError):
        sanitize_attributes(attrs)


@pytest.mark.parametrize(
    "labels",
    [
        {"case_id": "case-demo-42"},
        {"action_id": "action-demo-1"},
        {"model.version": "demo-model-v1"},
        {"evaluation.version": "finbench-eval-v1"},
        {"transaction_ref": "TXN-B"},
    ],
)
def test_rejects_correlation_metric_labels(labels: dict) -> None:
    with pytest.raises(RedactionError):
        sanitize_metric_labels(labels)


def test_allows_bounded_metric_labels() -> None:
    cleaned = sanitize_metric_labels(
        {
            "service": "finharness-runtime",
            "environment": "sandbox",
            "outcome": "ok",
            "model_class": "structured",
        }
    )
    assert cleaned["model_class"] == "structured"
