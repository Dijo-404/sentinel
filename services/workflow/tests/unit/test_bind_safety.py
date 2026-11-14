"""Non-loopback bind refuses demo bearer tokens."""

from __future__ import annotations

import pytest

from sentinel_workflow.adapters.bind_safety import UnsafeBindError, assert_loopback_or_non_demo


def test_loopback_ok() -> None:
    assert_loopback_or_non_demo("localhost", {"tok-workflow"})


def test_exposed_demo_refused() -> None:
    with pytest.raises(UnsafeBindError):
        assert_loopback_or_non_demo("192.168.1.10", {"tok-workflow", "secret-ok"})
