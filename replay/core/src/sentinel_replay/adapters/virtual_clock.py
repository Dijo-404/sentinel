from __future__ import annotations


class VirtualClock:
    """Deterministic virtual clock controlled by fixture event times."""

    def __init__(self, seed: int = 0) -> None:
        self._seed = seed
        self._now_s = 0

    def reset(self, seed: int) -> None:
        self._seed = seed
        self._now_s = 0

    def now_s(self) -> int:
        return self._now_s

    def advance_to(self, at_s: int) -> None:
        if at_s < self._now_s:
            raise ValueError(f"virtual clock cannot move backward: {at_s} < {self._now_s}")
        self._now_s = at_s

    @property
    def seed(self) -> int:
        return self._seed
