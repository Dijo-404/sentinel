"""Task-local typed snapshot of finbench.v1 and shared RunInput/RunReport shapes."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Literal

CONTRACT_VERSION = "sentinel.task-contracts.v1"
CONTRACT_SHA256 = "0db3ba2bba994f10d3060bc7173035360c15ffe23189cea409f7327e23c36feb"
PORT = "finbench.v1"

Mode = Literal["fixture", "real-peers"]
CheckStatus = Literal["PASS", "FAIL", "UNVERIFIED"]
RunStatus = Literal["PASS", "FAIL", "UNVERIFIED"]
EvidenceMode = Literal["fixture", "real-component", "live-provider"]
ModelLabel = Literal["fake", "live", "recorded"]
SplitName = Literal["dev", "val", "test"]


class ContractViolation(ValueError):
    """Payload failed local contract shape checks."""


class PeerError(RuntimeError):
    """Injected peer unavailable, malformed, unauthorized, or out of scope."""

    def __init__(
        self, peer: str, code: str, message: str, *, request_id: str = "request-local-1"
    ) -> None:
        self.peer = peer
        self.code = code
        self.message = message
        self.request_id = request_id
        super().__init__(f"{peer}: {code}: {message}")

    def as_error(self) -> dict[str, str]:
        return {"code": self.code, "message": self.message, "request_id": self.request_id}


@dataclass(frozen=True)
class CheckResult:
    name: str
    status: CheckStatus
    reason_code: str

    def to_dict(self) -> dict[str, str]:
        return {"name": self.name, "status": self.status, "reason_code": self.reason_code}


@dataclass(frozen=True)
class ArtifactRef:
    kind: str
    uri: str
    sha256: str
    component_version: str
    evidence_mode: EvidenceMode

    def to_dict(self) -> dict[str, str]:
        return {
            "kind": self.kind,
            "uri": self.uri,
            "sha256": self.sha256,
            "component_version": self.component_version,
            "evidence_mode": self.evidence_mode,
        }


@dataclass(frozen=True)
class RunInput:
    contract_version: str
    run_id: str
    mode: Mode
    input_artifacts: tuple[ArtifactRef, ...]
    parameters: Mapping[str, str | int | bool]

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> RunInput:
        if not isinstance(payload, Mapping):
            raise ContractViolation("RunInput must be an object")
        artifacts_raw = payload.get("input_artifacts")
        if not isinstance(artifacts_raw, list):
            raise ContractViolation("input_artifacts must be an array")
        artifacts = tuple(_artifact_from_mapping(item) for item in artifacts_raw)
        params = payload.get("parameters")
        if not isinstance(params, Mapping):
            raise ContractViolation("parameters must be an object")
        version = payload.get("contract_version")
        if version != CONTRACT_VERSION:
            raise ContractViolation(f"contract_version must be {CONTRACT_VERSION}")
        run_id = payload.get("run_id")
        if not isinstance(run_id, str) or not run_id:
            raise ContractViolation("run_id must be a non-empty string")
        mode = payload.get("mode")
        if mode not in {"fixture", "real-peers"}:
            raise ContractViolation("mode must be fixture|real-peers")
        return cls(
            contract_version=version,
            run_id=run_id,
            mode=mode,  # type: ignore[arg-type]
            input_artifacts=artifacts,
            parameters=dict(params),
        )


@dataclass(frozen=True)
class RunReport:
    contract_version: str
    run_id: str
    mode: Mode
    status: RunStatus
    checks: tuple[CheckResult, ...]
    output_artifacts: tuple[ArtifactRef, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "run_id": self.run_id,
            "mode": self.mode,
            "status": self.status,
            "checks": [c.to_dict() for c in self.checks],
            "output_artifacts": [a.to_dict() for a in self.output_artifacts],
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> RunReport:
        if not isinstance(payload, Mapping):
            raise ContractViolation("RunReport must be an object")
        checks_raw = payload.get("checks")
        arts_raw = payload.get("output_artifacts")
        if not isinstance(checks_raw, list) or not isinstance(arts_raw, list):
            raise ContractViolation("checks and output_artifacts must be arrays")
        version = payload.get("contract_version")
        if version != CONTRACT_VERSION:
            raise ContractViolation("contract_version mismatch")
        status = payload.get("status")
        if status not in {"PASS", "FAIL", "UNVERIFIED"}:
            raise ContractViolation("invalid status")
        mode = payload.get("mode")
        if mode not in {"fixture", "real-peers"}:
            raise ContractViolation("invalid mode")
        run_id = payload.get("run_id")
        if not isinstance(run_id, str) or not run_id:
            raise ContractViolation("run_id required")
        return cls(
            contract_version=version,
            run_id=run_id,
            mode=mode,  # type: ignore[arg-type]
            status=status,  # type: ignore[arg-type]
            checks=tuple(
                CheckResult(
                    name=str(c["name"]),
                    status=c["status"],  # type: ignore[arg-type]
                    reason_code=str(c["reason_code"]),
                )
                for c in checks_raw
            ),
            output_artifacts=tuple(_artifact_from_mapping(a) for a in arts_raw),
        )


def _artifact_from_mapping(payload: Any) -> ArtifactRef:
    if not isinstance(payload, Mapping):
        raise ContractViolation("ArtifactRef must be an object")
    mode = payload.get("evidence_mode")
    if mode not in {"fixture", "real-component", "live-provider"}:
        raise ContractViolation("invalid evidence_mode")
    return ArtifactRef(
        kind=str(payload["kind"]),
        uri=str(payload["uri"]),
        sha256=str(payload["sha256"]),
        component_version=str(payload["component_version"]),
        evidence_mode=mode,  # type: ignore[arg-type]
    )


@dataclass(frozen=True)
class ScoreBlock:
    """One labeled score channel with denominator and uncertainty."""

    label: str
    model_label: ModelLabel | Literal["system"]
    correct: int
    denominator: int
    mean: float
    variance: float
    abstained: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "model_label": self.model_label,
            "correct": self.correct,
            "denominator": self.denominator,
            "mean": self.mean,
            "variance": self.variance,
            "abstained": self.abstained,
        }


@dataclass(frozen=True)
class EvaluationReport:
    """finbench.v1 evaluation summary for a candidate run."""

    contract_version: str
    port: str
    baseline_sha256: str
    dataset_version: str
    dataset_sha256: str
    split: SplitName
    split_sha256: str
    candidate_id: str
    model_scores: tuple[ScoreBlock, ...]
    system_scores: tuple[ScoreBlock, ...]
    hard_safety_pass: bool
    hard_safety_failures: tuple[str, ...]
    overall_status: RunStatus
    evidence_mode: EvidenceMode
    checks: tuple[CheckResult, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "port": self.port,
            "baseline_sha256": self.baseline_sha256,
            "dataset_version": self.dataset_version,
            "dataset_sha256": self.dataset_sha256,
            "split": self.split,
            "split_sha256": self.split_sha256,
            "candidate_id": self.candidate_id,
            "model_scores": [s.to_dict() for s in self.model_scores],
            "system_scores": [s.to_dict() for s in self.system_scores],
            "hard_safety_pass": self.hard_safety_pass,
            "hard_safety_failures": list(self.hard_safety_failures),
            "overall_status": self.overall_status,
            "evidence_mode": self.evidence_mode,
            "checks": [c.to_dict() for c in self.checks],
        }
