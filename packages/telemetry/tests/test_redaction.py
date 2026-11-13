"""Redaction and bounded-label rejection boundaries."""

import pytest

from sentinel_telemetry import RedactionError, sanitize_attributes, sanitize_metric_labels


def test_allowlisted_correlation_attributes_pass() -> None:
    cleaned = sanitize_attributes(
        {
            "request_id": "request-demo-1",
            "case_id": "case-demo-42",
            "approval_id": "approval-demo-1",
            "worker_id": "worker-demo-1",
            "provider_ref": "refund-demo-1",
            "action_id": "action-demo-1",
            "error.type": "timeout",
        }
    )
    assert cleaned["case_id"] == "case-demo-42"
    assert cleaned["error.type"] == "timeout"


@pytest.mark.parametrize(
    "attrs",
    [
        {"authorization": "Bearer sk-secret-token-value0123"},
        {"api_key": "sk-abcdefghijklmnopqrstuvwxyz"},
        {"complaint": "I was charged twice for this order"},
        {"message": "please refund immediately"},
        {"prompt": "full unredacted model prompt text"},
        {"transaction_ref": "TXN-B"},
        {"order_reference": "DEMO-ORDER-42"},
        {"subject_ref": "subject-1"},
        {"customer_id": "cust-1"},
        {"raw_payload": "secret-stuff"},
        {"case_id": "case-demo-42", "otp": "123456"},
    ],
)
def test_forbidden_attributes_rejected(attrs: dict) -> None:
    with pytest.raises(RedactionError):
        sanitize_attributes(attrs)


@pytest.mark.parametrize(
    "labels",
    [
        {"case_id": "case-demo-42"},
        {"request_id": "request-demo-1"},
        {"approval_id": "approval-demo-1"},
        {"provider_ref": "refund-demo-1"},
        {"transaction_ref": "TXN-B"},
        {"order_reference": "DEMO-ORDER-42"},
        {"customer_id": "cust-1"},
        {"subject_ref": "subject-1"},
        {"unknown_label": "x"},
        {"service": "dispatcher", "secret": "x"},
    ],
)
def test_forbidden_metric_labels_rejected(labels: dict) -> None:
    with pytest.raises(RedactionError):
        sanitize_metric_labels(labels)


def test_bounded_metric_labels_pass() -> None:
    cleaned = sanitize_metric_labels(
        {
            "service": "dispatcher",
            "environment": "sandbox",
            "outcome": "timeout",
            "provider": "simulator",
            "error_type": "timeout",
        }
    )
    assert cleaned["outcome"] == "timeout"


def test_metric_label_cardinality_bound() -> None:
    labels = {
        name: "x"
        for name in sorted(
            [
                "service",
                "environment",
                "outcome",
                "scenario",
                "tool",
                "action_type",
                "provider",
                "error_type",
                "queue",
            ]
        )
    }
    with pytest.raises(RedactionError):
        sanitize_metric_labels(labels)
