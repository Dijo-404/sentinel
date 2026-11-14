"""Non-loopback bind refuses demo bearer tokens."""

from __future__ import annotations

import pytest

from sentinel_action_ledger.adapters.auth_tokens import principals_from_environ
from sentinel_action_ledger.adapters.bind_safety import (
    UnsafeBindError,
    assert_loopback_or_non_demo,
)


def test_loopback_allows_demo_tokens() -> None:
    assert_loopback_or_non_demo("127.0.0.1", {"tok-workflow"})


def test_non_loopback_refuses_demo_tokens() -> None:
    with pytest.raises(UnsafeBindError, match="non-loopback"):
        assert_loopback_or_non_demo("0.0.0.0", {"tok-dispatcher"})


def test_principals_from_environ_drops_aliases_off_loopback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LEDGER_HOST", "0.0.0.0")
    monkeypatch.setenv("LEDGER_TOKEN_WORKFLOW", "rot-workflow")
    monkeypatch.setenv("LEDGER_TOKEN_SUPERVISOR", "rot-supervisor")
    monkeypatch.setenv("LEDGER_TOKEN_DISPATCHER", "rot-dispatcher")
    monkeypatch.setenv("LEDGER_TOKEN_VERIFIER", "rot-verifier")
    mapping = principals_from_environ("tenant-demo")
    assert "tok-workflow" not in mapping
    assert "token-workflow-demo" not in mapping
    assert set(mapping) == {
        "rot-workflow",
        "rot-supervisor",
        "rot-dispatcher",
        "rot-verifier",
    }
    assert_loopback_or_non_demo("0.0.0.0", mapping.keys())
