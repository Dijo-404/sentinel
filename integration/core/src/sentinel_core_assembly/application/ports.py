"""Injected peer ports; no deep sibling imports."""

from __future__ import annotations

from typing import Protocol

from sentinel_core_assembly.domain.types import Capabilities


class PeerPort(Protocol):
    port: str

    def capabilities(self) -> Capabilities: ...


class JourneyPeers(Protocol):
    """Minimal surface the journey drivers need from local or real peers."""

    def capabilities_by_port(self) -> dict[str, Capabilities]: ...

    def run_pending(self) -> dict[str, object]: ...

    def run_merchant_mismatch(self) -> dict[str, object]: ...

    def run_duplicate_payment(self) -> dict[str, object]: ...

    def run_refund_pending(self) -> dict[str, object]: ...
