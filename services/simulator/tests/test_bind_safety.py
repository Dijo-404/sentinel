"""Non-loopback bind refuses demo bearer tokens."""

from __future__ import annotations

import pytest

from sentinel_simulator.adapters.bind_safety import UnsafeBindError, assert_loopback_or_non_demo
from sentinel_simulator.composition.app import create_app


def test_loopback_allows_demo_tokens() -> None:
    assert_loopback_or_non_demo("127.0.0.1", {"tok-workflow", "tok-dispatcher"})


def test_non_loopback_refuses_demo_tokens() -> None:
    with pytest.raises(UnsafeBindError, match="non-loopback"):
        assert_loopback_or_non_demo("0.0.0.0", {"tok-workflow"})


def test_non_loopback_allows_rotated_secrets() -> None:
    assert_loopback_or_non_demo("0.0.0.0", {"rot-workflow-9f", "rot-dispatcher-9f"})


def test_create_app_refuses_exposed_demo_host(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SIMULATOR_HOST", "0.0.0.0")
    with pytest.raises(UnsafeBindError):
        create_app()
