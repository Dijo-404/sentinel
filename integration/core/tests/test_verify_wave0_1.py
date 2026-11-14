"""Wave 0–1 verify: body asserts fail without seed; pass with seed-shaped JSON."""

from __future__ import annotations

import pytest

from sentinel_core_assembly.adapters.verify_wave0_1 import (
    SEED_DISPUTE_ID,
    SEED_INVESTIGATION_ID,
    assert_disputes_body,
    assert_metrics_body,
    assert_risk_list_body,
)


def test_metrics_assert_rejects_error_and_wrong_merchant() -> None:
    with pytest.raises(AssertionError, match="error code"):
        assert_metrics_body({"code": "SNAPSHOT_NOT_FOUND"})
    with pytest.raises(AssertionError, match="merchant_ref"):
        assert_metrics_body(
            {
                "merchant_ref": "other",
                "exception_rate": "0.1",
                "unresolved_minor": 1,
            }
        )


def test_metrics_assert_accepts_seed_shape() -> None:
    assert_metrics_body(
        {
            "merchant_ref": "merchant-demo-1",
            "exception_rate": "0.4000",
            "unresolved_minor": 100000,
            "currency": "INR",
        }
    )


def test_disputes_assert_rejects_empty() -> None:
    with pytest.raises(AssertionError, match="empty"):
        assert_disputes_body({"disputes": []})


def test_disputes_assert_requires_seed_id() -> None:
    with pytest.raises(AssertionError, match="dispute-seed-demo-1"):
        assert_disputes_body({"disputes": [{"dispute_id": "other"}]})
    assert_disputes_body({"disputes": [{"dispute_id": SEED_DISPUTE_ID, "status": "OPEN"}]})


def test_risk_assert_rejects_empty_and_requires_seed() -> None:
    with pytest.raises(AssertionError, match="empty"):
        assert_risk_list_body({"investigations": []})
    with pytest.raises(AssertionError, match="inv-seed-case-demo-42"):
        assert_risk_list_body({"investigations": [{"investigation_id": "x"}]})
    assert_risk_list_body({"investigations": [{"investigation_id": SEED_INVESTIGATION_ID}]})
