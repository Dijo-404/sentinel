from __future__ import annotations

from collections.abc import Mapping
from typing import Any


class MalformedRuntime:
    def capabilities(self) -> Mapping[str, Any]:
        return {"component": "finharness-runtime"}

    def run(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        _ = request
        return {"status": "PASS"}
