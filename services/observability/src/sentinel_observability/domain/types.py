"""Wire-aligned types matching packages/telemetry RecordedSpan shape."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

CONTRACT_VERSION = "sentinel.task-contracts.v1"
CONTRACT_SHA256 = "0db3ba2bba994f10d3060bc7173035360c15ffe23189cea409f7327e23c36feb"
PORT = "observability.v1"
FEED_LIMIT = 50
ADMIN_ROLES = frozenset({"platform_admin", "sandbox-admin"})

SignalKind = Literal["span", "metric"]
AttrValue = str | int | bool


@dataclass(frozen=True, slots=True)
class Principal:
    principal_id: str
    tenant_id: str
    roles: tuple[str, ...]

    def is_admin(self) -> bool:
        return bool(ADMIN_ROLES & set(self.roles))


@dataclass(frozen=True)
class Signal:
    """
    Persisted telemetry signal.

    Span wire fields (`name`, `attributes`, `events`) match
    `sentinel_telemetry.contracts.RecordedSpan` conceptually — not financial audit.
    """

    signal_id: str
    tenant_id: str
    kind: SignalKind
    name: str
    attributes: dict[str, AttrValue]
    events: list[dict[str, Any]] = field(default_factory=list)
    recorded_at: str = ""
    value: float | None = None
    labels: dict[str, str] = field(default_factory=dict)

    def to_wire(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "signal_id": self.signal_id,
            "kind": self.kind,
            "name": self.name,
            "attributes": dict(self.attributes),
            "events": list(self.events),
            "recorded_at": self.recorded_at,
        }
        return payload

    def to_span_wire(self) -> dict[str, Any]:
        """Telemetry RecordedSpan-shaped projection."""
        return {
            "name": self.name,
            "attributes": dict(self.attributes),
            "events": list(self.events),
        }
