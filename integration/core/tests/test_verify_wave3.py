"""Wave 3 verify: body asserts fail without seed; pass with seed-shaped JSON."""

from __future__ import annotations

import pytest

from sentinel_core_assembly.adapters.verify_wave3 import (
    SEED_CUSTOMER_DISPLAY_NAME,
    SEED_CUSTOMER_EMAIL,
    SEED_CUSTOMER_PREFERRED_LANGUAGE,
    SEED_CUSTOMER_USER_ID,
    SEED_NOTIFICATION_ID,
    assert_forgot_accepted,
    assert_forgot_no_enumeration,
    assert_me_body,
    assert_notifications_body,
    assert_workspaces_body,
    verify_wave3,
)


def test_defaults_match_identity_seed_principals() -> None:
    assert SEED_CUSTOMER_EMAIL == "customer@example.test"
    assert SEED_CUSTOMER_USER_ID == "11111111-1111-1111-1111-111111111101"
    assert SEED_NOTIFICATION_ID == "11111111-1111-1111-1111-111111111301"
    assert SEED_CUSTOMER_PREFERRED_LANGUAGE == "en"


def test_me_assert_rejects_missing_profile_fields() -> None:
    with pytest.raises(AssertionError, match="me.user missing"):
        assert_me_body({})
    with pytest.raises(AssertionError, match="preferred_language"):
        assert_me_body(
            {
                "user": {
                    "user_id": SEED_CUSTOMER_USER_ID,
                    "email": SEED_CUSTOMER_EMAIL,
                    "display_name": SEED_CUSTOMER_DISPLAY_NAME,
                    "preferred_language": "",
                }
            }
        )
    assert_me_body(
        {
            "user": {
                "user_id": SEED_CUSTOMER_USER_ID,
                "email": SEED_CUSTOMER_EMAIL,
                "display_name": SEED_CUSTOMER_DISPLAY_NAME,
                "preferred_language": SEED_CUSTOMER_PREFERRED_LANGUAGE,
            }
        }
    )


def test_notifications_assert_rejects_empty_and_requires_seed_id() -> None:
    with pytest.raises(AssertionError, match="empty"):
        assert_notifications_body({"notifications": []})
    with pytest.raises(AssertionError, match="seed notification"):
        assert_notifications_body({"notifications": [{"notification_id": "other", "title": "x"}]})
    assert_notifications_body(
        {
            "notifications": [
                {
                    "notification_id": SEED_NOTIFICATION_ID,
                    "title": "Welcome to Sentinel",
                }
            ]
        }
    )


def test_workspaces_assert_rejects_empty_and_requires_customer() -> None:
    with pytest.raises(AssertionError, match="empty"):
        assert_workspaces_body({"workspaces": []})
    with pytest.raises(AssertionError, match="customer workspace"):
        assert_workspaces_body({"workspaces": [{"role_id": "merchant"}]})
    assert_workspaces_body({"workspaces": [{"role_id": "customer", "tenant_id": "tenant-demo"}]})


def test_forgot_assert_requires_202_and_rejects_enum_shape() -> None:
    with pytest.raises(AssertionError, match="202"):
        assert_forgot_accepted(200, {"status": "accepted"})
    assert_forgot_accepted(202, {"status": "accepted"})
    with pytest.raises(AssertionError, match="enumeration"):
        assert_forgot_no_enumeration(
            202,
            {"status": "accepted", "exists": True},
            202,
            {"status": "accepted"},
        )
    assert_forgot_no_enumeration(
        202,
        {"status": "accepted"},
        202,
        {"status": "accepted"},
    )


def test_verify_wave3_fails_closed_when_peers_down(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VERIFY_IDENTITY_URL", "http://127.0.0.1:1")
    monkeypatch.delenv("VERIFY_IDENTITY_TOKEN", raising=False)
    report = verify_wave3(dict(__import__("os").environ))
    assert report["status"] == "FAIL"
    assert report.get("reason_code") == "WAVE3_VERIFY_FAILED"
    assert any(not c.get("ok") for c in report["checks"])


def test_verify_wave3_refuses_matrix_tok_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VERIFY_IDENTITY_URL", "http://127.0.0.1:8012")
    monkeypatch.setenv("VERIFY_IDENTITY_TOKEN", "tok-customer")
    report = verify_wave3(dict(__import__("os").environ))
    assert report["status"] == "FAIL"
    assert any("tok-" in (c.get("detail") or "") for c in report["checks"])
