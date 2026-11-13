from __future__ import annotations

from collections.abc import Mapping
from typing import Any


class MalformedIndicContext:
    def propose(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        _ = request
        return {"outcome": "PROPOSAL", "reason_codes": []}
