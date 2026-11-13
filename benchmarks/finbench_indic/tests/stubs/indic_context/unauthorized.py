from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from sentinel_finbench.contracts import PeerError


class UnauthorizedIndicContext:
    def propose(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        _ = request
        raise PeerError(
            "indic-context.v1",
            "unauthorized_or_out_of_scope",
            "model principal denied for tenant",
        )
