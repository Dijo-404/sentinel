"""Non-loopback bind refuses demo bearer tokens."""

from __future__ import annotations

import pytest

from sentinel_merchant_inbox.adapters.bind_safety import (
    UnsafeBindError,
    assert_loopback_or_non_demo,
)


def test_loopback_ok() -> None:
    assert_loopback_or_non_demo("::1", {"merchant-op-demo-token"})


def test_exposed_refused() -> None:
    with pytest.raises(UnsafeBindError):
        assert_loopback_or_non_demo("0.0.0.0", {"merchant-op-demo-token"})
