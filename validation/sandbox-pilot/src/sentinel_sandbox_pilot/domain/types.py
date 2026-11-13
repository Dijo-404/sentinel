"""Typed snapshot of sandbox-validation.v1 and shared RunInput/RunReport shapes."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

CONTRACT_VERSION = "sentinel.task-contracts.v1"
CONTRACT_SHA256 = "0c728513e8b4ec0f34bcef63faa0207160d45cc7f20f872c1d9136ca7e252ffa"
PORT = "sandbox-validation.v1"

Mode = Literal["fixture", "real-peers"]
ReportStatus = Literal["PASS", "FAIL", "UNVERIFIED"]
CheckStatus = Literal["PASS", "FAIL", "UNVERIFIED"]
EvidenceMode = Literal["fixture", "real-component", "live-provider"]
PilotVerdict = Literal["KIT_ONLY", "PASS", "FAIL", "UNVERIFIED", "NOT_AUTHORIZED"]

REQUIRED_PEERS = (
    "core-assembly.v1",
    "finharness-runtime.v1",
    "finbench.v1",
    "harness-telemetry.v1",
    "harness-replay.v1",
)

DRIVERS = (
    "second_workflow",
    "load",
    "restart",
    "restore",
    "kill_switch",
    "rollback",
)

DEMO_ACTION_ID = "action-sandbox-26"
DEMO_PROVIDER_REF = "refund-sandbox-26"
DEMO_AMOUNT_MINOR = 150_000
DEMO_RUNTIME_PIN = "finharness-runtime-fixture-v1"


@dataclass(frozen=True)
class CheckResult:
    name: str
    status: CheckStatus
    reason_code: str

    def as_dict(self) -> dict[str, str]:
        return {"name": self.name, "status": self.status, "reason_code": self.reason_code}


@dataclass(frozen=True)
class ArtifactRef:
    kind: str
    uri: str
    sha256: str
    component_version: str
    evidence_mode: EvidenceMode

    def as_dict(self) -> dict[str, str]:
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
    input_artifacts: tuple[ArtifactRef, ...] = ()
    parameters: dict[str, str | int | bool] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> RunInput:
        artifacts = tuple(
            ArtifactRef(
                kind=str(item["kind"]),
                uri=str(item["uri"]),
                sha256=str(item["sha256"]),
                component_version=str(item["component_version"]),
                evidence_mode=item["evidence_mode"],
            )
            for item in raw.get("input_artifacts", [])
        )
        return cls(
            contract_version=str(raw["contract_version"]),
            run_id=str(raw["run_id"]),
            mode=raw["mode"],
            input_artifacts=artifacts,
            parameters=dict(raw.get("parameters", {})),
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "run_id": self.run_id,
            "mode": self.mode,
            "input_artifacts": [a.as_dict() for a in self.input_artifacts],
            "parameters": dict(self.parameters),
        }


@dataclass(frozen=True)
class RunReport:
    contract_version: str
    run_id: str
    mode: Mode
    status: ReportStatus
    checks: tuple[CheckResult, ...]
    output_artifacts: tuple[ArtifactRef, ...] = ()
    external_pilot_claimed: bool = False
    pilot_verdict: PilotVerdict = "KIT_ONLY"

    def as_dict(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "run_id": self.run_id,
            "mode": self.mode,
            "status": self.status,
            "checks": [c.as_dict() for c in self.checks],
            "output_artifacts": [a.as_dict() for a in self.output_artifacts],
            "external_pilot_claimed": self.external_pilot_claimed,
            "pilot_verdict": self.pilot_verdict,
            "port": PORT,
            "contract_sha256": CONTRACT_SHA256,
        }


@dataclass(frozen=True)
class Capabilities:
    contract_version: str
    component: str
    mode: Mode
    port: str
