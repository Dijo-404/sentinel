"""Wave 2 verify: body asserts fail without seed; pass with seed-shaped JSON."""

from __future__ import annotations

import pytest

from sentinel_core_assembly.adapters.verify_wave2 import (
    DEFAULT_OPERATOR_TOKEN,
    DEFAULT_SUPERVISOR_TOKEN,
    SEED_ESCALATED_CASE_ID,
    SEED_HISTORY_CASE_ID,
    assert_audit_events_body,
    assert_escalated_body,
    assert_history_body,
    assert_messages_body,
    assert_ops_team_body,
    verify_wave2,
)


def test_defaults_match_case_api_fixture_tokens() -> None:
    assert DEFAULT_OPERATOR_TOKEN == "token-operator"
    assert DEFAULT_SUPERVISOR_TOKEN == "token-supervisor"


def test_escalated_assert_rejects_empty() -> None:
    with pytest.raises(AssertionError, match="empty"):
        assert_escalated_body({"cases": []})


def test_escalated_assert_requires_seed_id() -> None:
    with pytest.raises(AssertionError, match="case-seed-ops-escalated"):
        assert_escalated_body({"cases": [{"case_id": "other", "status": "ESCALATED"}]})
    assert_escalated_body({"cases": [{"case_id": SEED_ESCALATED_CASE_ID, "status": "ESCALATED"}]})


def test_history_assert_rejects_empty_and_requires_seed() -> None:
    with pytest.raises(AssertionError, match="empty"):
        assert_history_body({"cases": []})
    with pytest.raises(AssertionError, match="case-seed-ops-history"):
        assert_history_body({"cases": [{"case_id": "x", "status": "CLOSED_NO_ACTION"}]})
    assert_history_body(
        {"cases": [{"case_id": SEED_HISTORY_CASE_ID, "status": "CLOSED_NO_ACTION"}]}
    )
    assert_history_body(
        {"cases": [{"case_id": SEED_HISTORY_CASE_ID, "status": "VERIFIED_RESOLVED"}]}
    )


def test_messages_assert_rejects_empty_and_requires_seed_case() -> None:
    with pytest.raises(AssertionError, match="empty"):
        assert_messages_body({"messages": []})
    with pytest.raises(AssertionError, match="seed message"):
        assert_messages_body({"messages": [{"case_id": "other", "message_id": "m1"}]})
    assert_messages_body({"messages": [{"case_id": SEED_ESCALATED_CASE_ID, "message_id": "m1"}]})


def test_audit_assert_rejects_empty_and_requires_seed_case() -> None:
    with pytest.raises(AssertionError, match="empty"):
        assert_audit_events_body({"events": []})
    with pytest.raises(AssertionError, match="seed audit"):
        assert_audit_events_body({"events": [{"case_id": "other", "sequence": 1}]})
    assert_audit_events_body(
        {"events": [{"case_id": SEED_HISTORY_CASE_ID, "sequence": 1, "type": "CASE_CLOSED"}]}
    )


def test_ops_team_assert_rejects_empty() -> None:
    with pytest.raises(AssertionError, match="empty"):
        assert_ops_team_body({"members": []})
    assert_ops_team_body({"members": [{"email": "supervisor@example.test", "role": "supervisor"}]})


def test_verify_wave2_fails_closed_when_peers_down(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VERIFY_CASE_API_URL", "http://127.0.0.1:1")
    monkeypatch.delenv("VERIFY_IDENTITY_TOKEN", raising=False)
    report = verify_wave2(dict(__import__("os").environ))
    assert report["status"] == "FAIL"
    assert report.get("reason_code") == "WAVE2_VERIFY_FAILED"
    assert any(not c.get("ok") for c in report["checks"] if c["name"].startswith("case-api"))
