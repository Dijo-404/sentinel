"""Non-loopback bind refuses demo bearer tokens."""

from __future__ import annotations

import pytest

from sentinel_merchant_teams.adapters.bind_safety import (
    UnsafeBindError,
    assert_loopback_or_non_demo,
)


def test_loopback_ok() -> None:
    assert_loopback_or_non_demo("localhost", {"operator-token"})


def test_exposed_refused() -> None:
    with pytest.raises(UnsafeBindError):
        assert_loopback_or_non_demo("10.0.0.5", {"operator-token"})
