"""finharness-runtime.v1 stub cases."""

from __future__ import annotations

from typing import Any

from sentinel_finharness_telemetry.contracts import CONTRACT_VERSION, PeerError


class ValidRuntime:
    def observe_case(self, case_id: str) -> dict[str, Any]:
        return {
            "contract_version": CONTRACT_VERSION,
            "case_id": case_id,
            "action_id": "action-demo-1",
            "model_version": "demo-model-v1",
            "runtime_version": "finharness-runtime-v1",
            "mode": "fixture",
            "evidence_mode": "fixture",
        }


class UnavailableRuntime:
    def observe_case(self, case_id: str) -> dict[str, Any]:
        _ = case_id
        raise PeerError("finharness-runtime.v1", "unavailable", "runtime peer not reachable")


class MalformedRuntime:
    def observe_case(self, case_id: str) -> dict[str, Any]:
        return {"case_id": case_id, "model_version": 12.5}


class UnauthorizedRuntime:
    def observe_case(self, case_id: str) -> dict[str, Any]:
        _ = case_id
        raise PeerError(
            "finharness-runtime.v1",
            "unauthorized_or_out_of_scope",
            "case not in principal scope",
        )
