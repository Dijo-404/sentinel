"""Narrow ports for consumed peer Run* boundaries."""

from __future__ import annotations

from typing import Protocol

from sentinel_release_mvp.contracts import RunInput, RunReport


class PeerRunner(Protocol):
    """Injected adapter for a consumed library/CLI port."""

    port: str

    def run(self, request: RunInput) -> RunReport:
        """Execute peer; must raise PeerError on unavailable/malformed/unauthorized."""
        ...
