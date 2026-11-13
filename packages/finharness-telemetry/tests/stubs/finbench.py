"""finbench.v1 stub cases."""

from __future__ import annotations

from typing import Any

from sentinel_finharness_telemetry.contracts import CONTRACT_VERSION, PeerError


class ValidFinbench:
    def observe_evaluation(self, suite_id: str) -> dict[str, Any]:
        return {
            "contract_version": CONTRACT_VERSION,
            "suite_id": suite_id,
            "evaluation_version": "finbench-eval-v1",
            "dataset_version": "finbench-indic-demo-v1",
            "hard_safety_pass": True,
            "mode": "fixture",
            "evidence_mode": "fixture",
        }


class UnavailableFinbench:
    def observe_evaluation(self, suite_id: str) -> dict[str, Any]:
        _ = suite_id
        raise PeerError("finbench.v1", "unavailable", "finbench peer not reachable")


class MalformedFinbench:
    def observe_evaluation(self, suite_id: str) -> dict[str, Any]:
        return {"suite_id": suite_id, "scores": "not-a-map"}


class UnauthorizedFinbench:
    def observe_evaluation(self, suite_id: str) -> dict[str, Any]:
        _ = suite_id
        raise PeerError(
            "finbench.v1",
            "unauthorized_or_out_of_scope",
            "suite not authorized for principal",
        )
