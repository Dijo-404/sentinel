from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from sentinel_finbench.contracts import PeerError


class UnavailableIndicContext:
    def propose(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        _ = request
        raise PeerError("indic-context.v1", "unavailable", "indic-context peer not reachable")
