"""Non-loopback bind refuses demo credentials."""

from __future__ import annotations

import pytest

from sentinel_identity.adapters.bind_safety import UnsafeBindError, assert_loopback_or_non_demo
from sentinel_identity.adapters.seed import DEMO_PASSWORD


def test_loopback_allows_demo() -> None:
    assert_loopback_or_non_demo("127.0.0.1", [DEMO_PASSWORD])


def test_non_loopback_refuses_demo() -> None:
    with pytest.raises(UnsafeBindError):
        assert_loopback_or_non_demo("0.0.0.0", [DEMO_PASSWORD])


def test_sandbox_public_bind_allows_demo(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SENTINEL_SANDBOX_PUBLIC_BIND", "1")
    assert_loopback_or_non_demo("0.0.0.0", [DEMO_PASSWORD])
    assert_loopback_or_non_demo("0.0.0.0", ["demo-password"])
