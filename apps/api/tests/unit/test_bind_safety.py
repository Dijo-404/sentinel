"""Non-loopback bind refuses demo bearer tokens."""

from __future__ import annotations

import pytest

from sentinel_api.adapters.bind_safety import UnsafeBindError, assert_loopback_or_non_demo
from sentinel_api.config import Settings


def test_loopback_allows_demo() -> None:
    assert_loopback_or_non_demo("127.0.0.1", {"tok-case-api"})


def test_exposed_refuses_demo() -> None:
    with pytest.raises(UnsafeBindError):
        assert_loopback_or_non_demo("0.0.0.0", {"tok-case-api"})


def test_exposed_refuses_fixture_session_credentials() -> None:
    with pytest.raises(UnsafeBindError):
        assert_loopback_or_non_demo("0.0.0.0", {"sess-operator-1"})
    with pytest.raises(UnsafeBindError):
        assert_loopback_or_non_demo("0.0.0.0", {"sess-custom-demo"})


def test_settings_default_host_is_loopback() -> None:
    assert Settings().host == "127.0.0.1"
