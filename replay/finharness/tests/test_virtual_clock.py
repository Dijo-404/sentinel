from __future__ import annotations

import pytest

from sentinel_harness_replay.adapters.virtual_clock import VirtualClock


def test_virtual_clock_advances_monotonically() -> None:
    clock = VirtualClock(seed=42)
    assert clock.now_s() == 0
    clock.advance_to(6)
    assert clock.now_s() == 6
    clock.advance_to(15)
    assert clock.now_s() == 15
    with pytest.raises(ValueError):
        clock.advance_to(10)
    clock.reset(7)
    assert clock.seed == 7
    assert clock.now_s() == 0
