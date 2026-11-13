from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from sentinel_finbench.contracts import CONTRACT_VERSION


class ValidRuntime:
    def capabilities(self) -> Mapping[str, Any]:
        return {
            "contract_version": CONTRACT_VERSION,
            "component": "finharness-runtime",
            "mode": "fixture",
        }

    def run(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        return {
            "contract_version": CONTRACT_VERSION,
            "run_id": str(request.get("run_id", "runtime-fixture-1")),
            "mode": "fixture",
            "status": "PASS",
            "checks": [{"name": "shadow_compare", "status": "PASS", "reason_code": "OK"}],
            "output_artifacts": [],
        }
