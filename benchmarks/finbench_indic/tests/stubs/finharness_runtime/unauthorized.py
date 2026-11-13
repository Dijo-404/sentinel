from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from sentinel_finbench.contracts import PeerError


class UnauthorizedRuntime:
    def capabilities(self) -> Mapping[str, Any]:
        raise PeerError(
            "finharness-runtime.v1",
            "unauthorized_or_out_of_scope",
            "runtime principal denied for tenant",
        )

    def run(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        _ = request
        raise PeerError(
            "finharness-runtime.v1",
            "unauthorized_or_out_of_scope",
            "runtime principal denied for tenant",
        )
