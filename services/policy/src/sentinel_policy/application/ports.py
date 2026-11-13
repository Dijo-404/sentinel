"""Narrow ports used by policy use cases."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol


class Clock(Protocol):
    def now(self) -> datetime:
        """UTC instant used for expiry checks."""
