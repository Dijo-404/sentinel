"""Task-local typed snapshot of the harness-telemetry.v1 library boundary."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

CONTRACT_VERSION = "sentinel.task-contracts.v1"
CONTRACT_SHA256 = "0db3ba2bba994f10d3060bc7173035360c15ffe23189cea409f7327e23c36feb"
PORT = "harness-telemetry.v1"
COMPONENT_VERSION = "0.1.0"

Mode = Literal["fixture", "real-peers"]
CheckStatus = Literal["PASS", "FAIL", "UNVERIFIED"]
ReportStatus = Literal["PASS", "FAIL", "UNVERIFIED"]
EvidenceMode = Literal["fixture", "real-component", "live-provider"]


class HarnessTelemetryContractError(ValueError):
    """Invalid RunInput, unsupported option, or contract mismatch; no secrets."""


class RedactionError(ValueError):
    """Rejected attribute, metric label, or value that must not enter telemetry."""


class MissingExporterError(RuntimeError):
    """Base telemetry exporter was not injected."""


class PeerError(RuntimeError):
    """Consumed peer unavailable, malformed, or unauthorized."""

    def __init__(self, port: str, kind: str, message: str) -> None:
        self.port = port
        self.kind = kind
        super().__init__(f"{port}:{kind}:{message}")


@dataclass(frozen=True)
class ArtifactRef:
    kind: str
    uri: str
    sha256: str
    component_version: str
    evidence_mode: EvidenceMode

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class CheckResult:
    name: str
    status: CheckStatus
    reason_code: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class RunInput:
    contract_version: Literal["sentinel.task-contracts.v1"]
    run_id: str
    mode: Mode
    input_artifacts: list[ArtifactRef]
    parameters: dict[str, str | int | bool]

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> RunInput:
        if not isinstance(raw, dict):
            raise HarnessTelemetryContractError("RunInput must be an object")
        unexpected = set(raw) - {
            "contract_version",
            "run_id",
            "mode",
            "input_artifacts",
            "parameters",
        }
        if unexpected:
            raise HarnessTelemetryContractError("RunInput rejects undeclared properties")
        for key in ("contract_version", "run_id", "mode", "input_artifacts", "parameters"):
            if key not in raw:
                raise HarnessTelemetryContractError(f"RunInput missing {key}")
        if raw["contract_version"] != CONTRACT_VERSION:
            raise HarnessTelemetryContractError("Unsupported required contract version")
        if raw["mode"] not in ("fixture", "real-peers"):
            raise HarnessTelemetryContractError("mode must be fixture or real-peers")
        if not isinstance(raw["run_id"], str) or not raw["run_id"]:
            raise HarnessTelemetryContractError("run_id must be a nonempty string")
        if not isinstance(raw["input_artifacts"], list):
            raise HarnessTelemetryContractError("input_artifacts must be an array")
        if not isinstance(raw["parameters"], dict):
            raise HarnessTelemetryContractError("parameters must be an object")
        for key, value in raw["parameters"].items():
            if not isinstance(key, str):
                raise HarnessTelemetryContractError("parameter keys must be strings")
            if isinstance(value, bool) or isinstance(value, str):
                continue
            if isinstance(value, int) and not isinstance(value, bool):
                continue
            raise HarnessTelemetryContractError("parameters values must be string, int, or bool")
        artifacts: list[ArtifactRef] = []
        for item in raw["input_artifacts"]:
            if not isinstance(item, dict):
                raise HarnessTelemetryContractError("ArtifactRef must be an object")
            try:
                artifacts.append(
                    ArtifactRef(
                        kind=item["kind"],
                        uri=item["uri"],
                        sha256=item["sha256"],
                        component_version=item["component_version"],
                        evidence_mode=item["evidence_mode"],
                    )
                )
            except KeyError as exc:
                raise HarnessTelemetryContractError("ArtifactRef missing required field") from exc
            if artifacts[-1].evidence_mode not in ("fixture", "real-component", "live-provider"):
                raise HarnessTelemetryContractError("Invalid evidence_mode")
        return cls(
            contract_version="sentinel.task-contracts.v1",
            run_id=raw["run_id"],
            mode=raw["mode"],
            input_artifacts=artifacts,
            parameters=dict(raw["parameters"]),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "run_id": self.run_id,
            "mode": self.mode,
            "input_artifacts": [a.to_dict() for a in self.input_artifacts],
            "parameters": dict(self.parameters),
        }


@dataclass(frozen=True)
class RunReport:
    contract_version: Literal["sentinel.task-contracts.v1"]
    run_id: str
    mode: Mode
    status: ReportStatus
    checks: list[CheckResult]
    output_artifacts: list[ArtifactRef]

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "run_id": self.run_id,
            "mode": self.mode,
            "status": self.status,
            "checks": [c.to_dict() for c in self.checks],
            "output_artifacts": [a.to_dict() for a in self.output_artifacts],
        }


@dataclass(frozen=True)
class HarnessCorrelation:
    """Joins case/action/model/evaluation versions. Not valid as Prometheus labels."""

    request_id: str
    case_id: str
    action_id: str
    model_version: str
    evaluation_version: str
    runtime_version: str = ""
    dataset_version: str = ""
    audit_event_key: str = ""

    def as_attributes(self) -> dict[str, str]:
        attrs = {
            "request_id": self.request_id,
            "case_id": self.case_id,
            "action_id": self.action_id,
            "model.version": self.model_version,
            "evaluation.version": self.evaluation_version,
        }
        if self.runtime_version:
            attrs["runtime.version"] = self.runtime_version
        if self.dataset_version:
            attrs["dataset.version"] = self.dataset_version
        if self.audit_event_key:
            attrs["audit.event_key"] = self.audit_event_key
        return attrs


@dataclass
class RecordedSpan:
    name: str
    attributes: dict[str, str | int | bool]
    events: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class RecordedMetric:
    name: str
    value: float
    labels: dict[str, str]


@dataclass(frozen=True)
class FinancialAuditRecord:
    """Authoritative financial audit is unsampled and owned outside telemetry."""

    event_key: str
    action_id: str
    outcome: str


@dataclass(frozen=True)
class AuditCorrelationRecord:
    """Telemetry-side link to an audit event. Never a substitute for the audit write."""

    audit_event_key: str
    action_id: str
    case_id: str
    request_id: str
