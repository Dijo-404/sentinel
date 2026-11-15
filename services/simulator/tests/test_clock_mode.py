"""SIMULATOR_CLOCK selects fixed demo instant vs real UTC time."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from sentinel_simulator.adapters.memory import InMemoryStore
from sentinel_simulator.composition.app import clock_from_env
from sentinel_simulator.domain.models import SimulatorClock


def test_default_clock_is_fixed_demo_instant(monkeypatch) -> None:
    monkeypatch.delenv("SIMULATOR_CLOCK", raising=False)
    assert clock_from_env().now() == "2026-11-13T12:00:00Z"


def test_system_clock_tracks_real_time(monkeypatch) -> None:
    monkeypatch.setenv("SIMULATOR_CLOCK", "system")
    stamp = datetime.strptime(clock_from_env().now(), "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    assert abs(datetime.now(UTC) - stamp) < timedelta(seconds=5)


def test_invalid_clock_mode_rejected(monkeypatch) -> None:
    monkeypatch.setenv("SIMULATOR_CLOCK", "later")
    with pytest.raises(ValueError):
        clock_from_env()


def test_demo_reset_keeps_system_clock() -> None:
    store = InMemoryStore(clock=SimulatorClock(instant=None))
    store.reset_runtime()
    assert store._clock.instant is None
