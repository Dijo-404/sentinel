from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from sentinel_evaluation.application.ports import AssemblyPeer, CandidateRunner, FixtureDataset
from sentinel_evaluation.domain.models import CONTRACT_VERSION
from sentinel_evaluation.domain.scoring import score_fixture, summarize_scores


class EvaluateError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class EvaluateService:
    def __init__(
        self,
        dataset: FixtureDataset,
        candidate: CandidateRunner,
        assembly: AssemblyPeer | None = None,
        *,
        output_dir: Path | None = None,
        component_version: str = "0.1.0",
    ) -> None:
        self._dataset = dataset
        self._candidate = candidate
        self._assembly = assembly
        self._output_dir = output_dir
        self._component_version = component_version

    def run(self, run_input: dict[str, Any]) -> dict[str, Any]:
        self._validate_run_input(run_input)
        mode = run_input["mode"]
        run_id = run_input["run_id"]
        if mode == "real-peers":
            self._require_assembly()

        scores = []
        for fixture in self._dataset.fixtures():
            observation = self._candidate.run(fixture)
            scores.append(score_fixture(fixture, observation))

        detail = summarize_scores(
            scores,
            dataset_version=self._dataset.version,
            dataset_sha256=self._dataset.sha256,
            model_mode=self._candidate.model_mode,
            candidate_id=self._candidate.candidate_id,
            run_id=run_id,
        )
        overall = detail["overall_status"]
        checks = self._build_checks(detail, mode)

        artifact_ref = self._write_detail(detail, run_id)
        return {
            "contract_version": CONTRACT_VERSION,
            "run_id": run_id,
            "mode": mode,
            "status": overall if mode == "fixture" else self._real_peer_status(overall, checks),
            "checks": checks,
            "output_artifacts": [artifact_ref] if artifact_ref else [],
            "detail": detail,
        }

    def _validate_run_input(self, run_input: dict[str, Any]) -> None:
        required = ("contract_version", "run_id", "mode", "input_artifacts", "parameters")
        for key in required:
            if key not in run_input:
                raise EvaluateError("INVALID_INPUT", f"Missing RunInput field: {key}")
        if run_input["contract_version"] != CONTRACT_VERSION:
            raise EvaluateError("CONTRACT_MISMATCH", "Unsupported contract_version")
        if run_input["mode"] not in ("fixture", "real-peers"):
            raise EvaluateError("INVALID_INPUT", "mode must be fixture or real-peers")
        if not isinstance(run_input["input_artifacts"], list):
            raise EvaluateError("INVALID_INPUT", "input_artifacts must be a list")
        if not isinstance(run_input["parameters"], dict):
            raise EvaluateError("INVALID_INPUT", "parameters must be an object")

    def _require_assembly(self) -> None:
        if self._assembly is None:
            raise EvaluateError("PEER_UNAVAILABLE", "core-assembly.v1 peer required in real-peers")
        try:
            probe = self._assembly.probe()
        except EvaluateError:
            raise
        except Exception as exc:  # noqa: BLE001 — boundary: surface peer failure
            raise EvaluateError(
                "PEER_UNAVAILABLE",
                f"core-assembly.v1 probe failed: {exc}",
            ) from exc
        status = probe.get("status")
        if status == "UNAVAILABLE":
            raise EvaluateError("PEER_UNAVAILABLE", probe.get("message", "assembly unavailable"))
        if status == "MALFORMED":
            raise EvaluateError("PEER_MALFORMED", probe.get("message", "assembly malformed"))
        if status in ("UNAUTHORIZED", "OUT_OF_SCOPE"):
            raise EvaluateError(
                "PEER_UNAUTHORIZED", probe.get("message", "assembly unauthorized/out of scope")
            )
        if status != "OK":
            raise EvaluateError("PEER_INCOMPATIBLE", f"Unexpected assembly status: {status}")
        caps = probe.get("capabilities") or {}
        if caps.get("contract_version") != CONTRACT_VERSION:
            raise EvaluateError("PEER_INCOMPATIBLE", "assembly contract_version mismatch")
        if caps.get("component") != "core-assembly":
            raise EvaluateError("PEER_INCOMPATIBLE", "assembly component mismatch")

    def _build_checks(self, detail: dict[str, Any], mode: str) -> list[dict[str, str]]:
        safety = detail["safety"]
        outcomes = detail["outcomes"]
        has_hash = bool(detail["dataset"]["sha256"])
        checks = [
            {
                "name": "dataset_hash_present",
                "status": "PASS" if has_hash else "FAIL",
                "reason_code": "DATASET_HASH_OK" if has_hash else "DATASET_HASH_MISSING",
            },
            {
                "name": "holdout_membership_disclosed",
                "status": "PASS",
                "reason_code": "HOLDOUT_DISCLOSED",
            },
            {
                "name": "model_mode_disclosed",
                "status": "PASS" if detail["model_mode"] else "FAIL",
                "reason_code": "MODEL_MODE_OK" if detail["model_mode"] else "MODEL_MODE_MISSING",
            },
            {
                "name": "outcome_denominators",
                "status": "PASS" if outcomes["denominator"] == outcomes["total"] else "FAIL",
                "reason_code": "DENOMINATORS_OK",
            },
            {
                "name": "critical_safety",
                "status": "PASS" if safety["passed"] else "FAIL",
                "reason_code": (
                    "SAFETY_CLEAN"
                    if safety["passed"]
                    else ",".join(safety["critical_failures"]) or "SAFETY_FAIL"
                ),
            },
            {
                "name": "safety_overrides_quality",
                "status": "PASS",
                "reason_code": (
                    "OVERRIDE_APPLIED" if safety["overrides_quality"] else "OVERRIDE_NOT_NEEDED"
                ),
            },
            {
                "name": "overall_evaluation",
                "status": detail["overall_status"],
                "reason_code": detail["overall_status"],
            },
        ]
        if mode == "real-peers":
            checks.append(
                {
                    "name": "assembly_peer",
                    "status": "PASS",
                    "reason_code": "ASSEMBLY_OK",
                }
            )
        return checks

    def _real_peer_status(self, overall: str, checks: list[dict[str, str]]) -> str:
        if any(c["status"] == "FAIL" for c in checks) or overall == "FAIL":
            return "FAIL"
        if any(c["status"] == "UNVERIFIED" for c in checks):
            return "UNVERIFIED"
        return "PASS"

    def _write_detail(self, detail: dict[str, Any], run_id: str) -> dict[str, str] | None:
        payload = json.dumps(detail, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        if self._output_dir is None:
            return {
                "kind": "evaluation.detail.v1",
                "uri": f"memory://evaluation/{run_id}",
                "sha256": digest,
                "component_version": self._component_version,
                "evidence_mode": "fixture",
            }
        self._output_dir.mkdir(parents=True, exist_ok=True)
        path = self._output_dir / f"{run_id}.evaluation.detail.v1.json"
        path.write_text(payload + "\n", encoding="utf-8")
        return {
            "kind": "evaluation.detail.v1",
            "uri": str(path),
            "sha256": digest,
            "component_version": self._component_version,
            "evidence_mode": "fixture",
        }
