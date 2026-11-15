"""Narrow ports used by policy use cases."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from sentinel_policy.domain.artifacts import PolicyArtifact


class Clock(Protocol):
    def now(self) -> datetime:
        """UTC instant used for expiry checks."""


class PolicyCatalogPort(Protocol):
    def list(self) -> tuple[PolicyArtifact, ...]:
        """Seeded versioned policy artifacts."""
