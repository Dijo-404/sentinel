"""Injected peer ports; no deep sibling imports."""

from __future__ import annotations

from typing import Any, Protocol

from sentinel_sandbox_pilot.domain.types import Capabilities


class PeerPort(Protocol):
    port: str

    def capabilities(self) -> Capabilities: ...


class ValidationPeers(Protocol):
    """Minimal surface drivers need from local or real peers."""

    def capabilities_by_port(self) -> dict[str, Capabilities]: ...

    def run_second_workflow(self) -> dict[str, Any]: ...

    def run_load(self, concurrency: int) -> dict[str, Any]: ...

    def run_restart(self) -> dict[str, Any]: ...

    def run_restore(self, *, fail_restore: bool = False) -> dict[str, Any]: ...

    def run_kill_switch(self) -> dict[str, Any]: ...

    def run_rollback(self) -> dict[str, Any]: ...
