"""Non-loopback bind refuses demo bearer tokens."""

from __future__ import annotations

import pytest

from sentinel_merchant_refunds.adapters.bind_safety import (
    UnsafeBindError,
    assert_loopback_or_non_demo,
)


def test_loopback_ok() -> None:
    assert_loopback_or_non_demo("127.0.0.1", {"token-merchant-refunds-demo"})


def test_exposed_refused() -> None:
    with pytest.raises(UnsafeBindError):
        assert_loopback_or_non_demo("0.0.0.0", {"token-merchant-refunds-demo"})
