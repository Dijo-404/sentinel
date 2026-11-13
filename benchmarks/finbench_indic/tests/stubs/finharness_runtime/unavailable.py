from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from sentinel_finbench.contracts import PeerError


class UnavailableRuntime:
    def capabilities(self) -> Mapping[str, Any]:
        raise PeerError("finharness-runtime.v1", "unavailable", "runtime peer not reachable")

    def run(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        _ = request
        raise PeerError("finharness-runtime.v1", "unavailable", "runtime peer not reachable")
