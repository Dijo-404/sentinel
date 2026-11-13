"""Task-local typed snapshot of release-evidence.v1 and shared Run* wire types."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Mapping

CONTRACT_VERSION = "sentinel.task-contracts.v1"
CONTRACT_SHA256 = (
    "0c728513e8b4ec0f34bcef63faa0207160d45cc7f20f872c1d9136ca7e252ffa"
)
PORT = "release-evidence.v1"
COMPONENT = "release-mvp"

Mode = Literal["fixture", "real-peers"]
Status = Literal["PASS", "FAIL", "UNVERIFIED"]
EvidenceMode = Literal["fixture", "real-component", "live-provider"]
ComponentUnderTest = Literal["real", "fixture"]
PaymentProvider = Literal["simulator", "external-sandbox"]
ModelEvidence = Literal["fake", "live"]

REQUIRED_PORTS = (
    "core-assembly.v1",
    "evaluation.v1",
    "replay.v1",
    "telemetry.v1",
)

REQUIRED_CHECK_NAMES = (
    "journey_duplicate_payment",
    "journey_partial_fulfillment",
    "journey_wrong_item",
    "journey_cancelled_order",
    "tenant_approval_boundary",
    "postgres_concurrency",
    "timeout_recovery",
    "webhook_recheck",
    "trace_correlation",
    "evaluation_report",
    "replay_promotion",
)


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

    @staticmethod
    def from_dict(data: Mapping[str, Any]) -> ArtifactRef:
        return ArtifactRef(
            kind=_req_str(data, "kind"),
            uri=_req_str(data, "uri"),
            sha256=_req_sha256(data, "sha256"),
            component_version=_req_str(data, "component_version"),
            evidence_mode=_req_enum(  # type: ignore[arg-type]
                data, "evidence_mode", ("fixture", "real-component", "live-provider")
            ),
        )


@dataclass(frozen=True)
class CheckResult:
    name: str
    status: Status
    reason_code: str

    def to_dict(self) -> dict[str, str]:
        return {
            "name": self.name,
            "status": self.status,
            "reason_code": self.reason_code,
        }

    @staticmethod
    def from_dict(data: Mapping[str, Any]) -> CheckResult:
        return CheckResult(
            name=_req_str(data, "name"),
            status=_req_enum(data, "status", ("PASS", "FAIL", "UNVERIFIED")),  # type: ignore[arg-type]
            reason_code=_req_str(data, "reason_code"),
        )


@dataclass(frozen=True)
class RunInput:
    contract_version: str
    run_id: str
    mode: Mode
    input_artifacts: tuple[ArtifactRef, ...]
    parameters: Mapping[str, str | int | bool]

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "run_id": self.run_id,
            "mode": self.mode,
            "input_artifacts": [a.to_dict() for a in self.input_artifacts],
            "parameters": dict(self.parameters),
        }

    @staticmethod
    def from_dict(data: Mapping[str, Any]) -> RunInput:
        arts = data.get("input_artifacts")
        if not isinstance(arts, list):
            raise ContractError("INVALID_INPUT", "input_artifacts must be an array")
        params = data.get("parameters")
        if not isinstance(params, dict):
            raise ContractError("INVALID_INPUT", "parameters must be an object")
        for key, value in params.items():
            if not isinstance(key, str) or not isinstance(value, (str, int, bool)):
                raise ContractError(
                    "INVALID_INPUT", "parameters values must be string|int|bool"
                )
            if isinstance(value, bool):
                continue
            if isinstance(value, int) and not isinstance(value, bool):
                continue
        return RunInput(
            contract_version=_req_str(data, "contract_version"),
            run_id=_req_str(data, "run_id"),
            mode=_req_enum(data, "mode", ("fixture", "real-peers")),  # type: ignore[arg-type]
            input_artifacts=tuple(ArtifactRef.from_dict(a) for a in arts),
            parameters=params,
        )


@dataclass(frozen=True)
class RunReport:
    contract_version: str
    run_id: str
    mode: Mode
    status: Status
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

    @staticmethod
    def from_dict(data: Mapping[str, Any]) -> RunReport:
        checks = data.get("checks")
        arts = data.get("output_artifacts")
        if not isinstance(checks, list) or not isinstance(arts, list):
            raise ContractError("INVALID_INPUT", "checks and output_artifacts must be arrays")
        return RunReport(
            contract_version=_req_str(data, "contract_version"),
            run_id=_req_str(data, "run_id"),
            mode=_req_enum(data, "mode", ("fixture", "real-peers")),  # type: ignore[arg-type]
            status=_req_enum(data, "status", ("PASS", "FAIL", "UNVERIFIED")),  # type: ignore[arg-type]
            checks=tuple(CheckResult.from_dict(c) for c in checks),
            output_artifacts=tuple(ArtifactRef.from_dict(a) for a in arts),
        )


@dataclass(frozen=True)
class ComponentEvidence:
    """Port-specific release-evidence record for one required peer component."""

    component: str
    port: str
    component_version: str
    component_commit: str
    contract_sha256: str
    check_command: str
    check_result: Status
    artifact_digest: str
    artifact_uri: str
    observed_mode: Mode
    evidence_mode: EvidenceMode
    observed_at: str

    def to_dict(self) -> dict[str, str]:
        return {
            "component": self.component,
            "port": self.port,
            "component_version": self.component_version,
            "component_commit": self.component_commit,
            "contract_sha256": self.contract_sha256,
            "check_command": self.check_command,
            "check_result": self.check_result,
            "artifact_digest": self.artifact_digest,
            "artifact_uri": self.artifact_uri,
            "observed_mode": self.observed_mode,
            "evidence_mode": self.evidence_mode,
            "observed_at": self.observed_at,
        }

    @staticmethod
    def from_dict(data: Mapping[str, Any]) -> ComponentEvidence:
        return ComponentEvidence(
            component=_req_str(data, "component"),
            port=_req_str(data, "port"),
            component_version=_req_str(data, "component_version"),
            component_commit=_req_str(data, "component_commit"),
            contract_sha256=_req_sha256(data, "contract_sha256"),
            check_command=_req_str(data, "check_command"),
            check_result=_req_enum(  # type: ignore[arg-type]
                data, "check_result", ("PASS", "FAIL", "UNVERIFIED")
            ),
            artifact_digest=_req_sha256(data, "artifact_digest"),
            artifact_uri=_req_str(data, "artifact_uri"),
            observed_mode=_req_enum(data, "observed_mode", ("fixture", "real-peers")),  # type: ignore[arg-type]
            evidence_mode=_req_enum(  # type: ignore[arg-type]
                data, "evidence_mode", ("fixture", "real-component", "live-provider")
            ),
            observed_at=_req_str(data, "observed_at"),
        )


@dataclass(frozen=True)
class EvidenceManifest:
    """release-evidence.v1 port-specific artifact schema."""

    contract_version: str
    manifest_id: str
    observed_at: str
    baseline_contract_sha256: str
    component_under_test: ComponentUnderTest
    payment_provider: PaymentProvider
    model: ModelEvidence
    components: tuple[ComponentEvidence, ...]
    required_checks: tuple[CheckResult, ...]
    attributes: Mapping[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "contract_version": self.contract_version,
            "manifest_id": self.manifest_id,
            "observed_at": self.observed_at,
            "baseline_contract_sha256": self.baseline_contract_sha256,
            "component_under_test": self.component_under_test,
            "payment_provider": self.payment_provider,
            "model": self.model,
            "components": [c.to_dict() for c in self.components],
            "required_checks": [c.to_dict() for c in self.required_checks],
        }
        if self.attributes:
            out["attributes"] = dict(self.attributes)
        return out

    @staticmethod
    def from_dict(data: Mapping[str, Any]) -> EvidenceManifest:
        if not isinstance(data, Mapping):
            raise ContractError("INVALID_INPUT", "manifest must be an object")
        allowed = {
            "contract_version",
            "manifest_id",
            "observed_at",
            "baseline_contract_sha256",
            "component_under_test",
            "payment_provider",
            "model",
            "components",
            "required_checks",
            "attributes",
        }
        extra = set(data) - allowed
        if extra:
            raise ContractError("INVALID_INPUT", f"undeclared properties: {sorted(extra)}")
        comps = data.get("components")
        checks = data.get("required_checks")
        if not isinstance(comps, list) or not isinstance(checks, list):
            raise ContractError(
                "INVALID_INPUT", "components and required_checks must be arrays"
            )
        attrs = data.get("attributes", {})
        if attrs is None:
            attrs = {}
        if not isinstance(attrs, dict) or any(
            not isinstance(k, str) or not isinstance(v, str) for k, v in attrs.items()
        ):
            raise ContractError("INVALID_INPUT", "attributes must be string map")
        return EvidenceManifest(
            contract_version=_req_str(data, "contract_version"),
            manifest_id=_req_str(data, "manifest_id"),
            observed_at=_req_str(data, "observed_at"),
            baseline_contract_sha256=_req_sha256(data, "baseline_contract_sha256"),
            component_under_test=_req_enum(  # type: ignore[arg-type]
                data, "component_under_test", ("real", "fixture")
            ),
            payment_provider=_req_enum(  # type: ignore[arg-type]
                data, "payment_provider", ("simulator", "external-sandbox")
            ),
            model=_req_enum(data, "model", ("fake", "live")),  # type: ignore[arg-type]
            components=tuple(ComponentEvidence.from_dict(c) for c in comps),
            required_checks=tuple(CheckResult.from_dict(c) for c in checks),
            attributes={str(k): str(v) for k, v in attrs.items()},
        )


@dataclass(frozen=True)
class ReleaseVerdict:
    """Kit-local verdict; PASS self-test never implies release_approved."""

    release_approved: bool
    status: Status
    reason_codes: tuple[str, ...]
    checks: tuple[CheckResult, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "release_approved": self.release_approved,
            "status": self.status,
            "reason_codes": list(self.reason_codes),
            "checks": [c.to_dict() for c in self.checks],
        }


class ContractError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class PeerError(Exception):
    def __init__(self, code: str, message: str, request_id: str = "request-local-1") -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.request_id = request_id

    def to_error(self) -> dict[str, str]:
        return {
            "code": self.code,
            "message": self.message,
            "request_id": self.request_id,
        }


def _req_str(data: Mapping[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise ContractError("INVALID_INPUT", f"{key} must be a non-empty string")
    return value


def _req_sha256(data: Mapping[str, Any], key: str) -> str:
    value = _req_str(data, key)
    if len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise ContractError("INVALID_INPUT", f"{key} must be lowercase sha256 hex")
    return value


def _req_enum(data: Mapping[str, Any], key: str, allowed: tuple[str, ...]) -> str:
    value = _req_str(data, key)
    if value not in allowed:
        raise ContractError("INVALID_INPUT", f"{key} must be one of {allowed}")
    return value
