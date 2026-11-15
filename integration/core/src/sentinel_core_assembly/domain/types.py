"""Typed snapshot of core-assembly.v1 and shared RunInput/RunReport shapes."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

CONTRACT_VERSION = "sentinel.task-contracts.v1"
CONTRACT_SHA256 = "0db3ba2bba994f10d3060bc7173035360c15ffe23189cea409f7327e23c36feb"
PORT = "core-assembly.v1"

Mode = Literal["fixture", "real-peers"]
ReportStatus = Literal["PASS", "FAIL", "UNVERIFIED"]
CheckStatus = Literal["PASS", "FAIL", "UNVERIFIED"]
EvidenceMode = Literal["fixture", "real-component", "live-provider"]

REQUIRED_PEERS = (
    "case-api.v1",
    "workflow.v1",
    "action-ledger.v1",
    "dispatcher.v1",
    "verifier.v1",
    "payment-provider.v1",
    "web-shell.v1",
)

# Provider-HTTP sandbox journeys (path=provider-sandbox-only when alone).
PROVIDER_JOURNEYS = (
    "pending",
    "merchant_mismatch",
    "duplicate_payment",
    "refund_pending",
)

# Intake→ledger→dispatcher→verifier→closure (SN-009 authority structure).
AUTHORITY_JOURNEYS = (
    "browser_to_credit",
    "duplicate_approval_deny",
)

JOURNEYS = PROVIDER_JOURNEYS + AUTHORITY_JOURNEYS

DUPLICATE_AMOUNT_MINOR = 150_000
AUTHORITY_PATH = "browser-to-credit"
AUTHORITY_FIXTURE_PATH = "browser-to-credit-fixture"
PROVIDER_ONLY_PATH = "provider-sandbox-only"
FIXTURE_PATH = "fixture-reference"


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
    assembled_mvp_claimed: bool = False
    payment_provider: str | None = None
    path: str | None = None
    sn009_authority_exercised: bool = False

    def as_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "contract_version": self.contract_version,
            "run_id": self.run_id,
            "mode": self.mode,
            "status": self.status,
            "checks": [c.as_dict() for c in self.checks],
            "output_artifacts": [a.as_dict() for a in self.output_artifacts],
            "assembled_mvp_claimed": self.assembled_mvp_claimed,
            "sn009_authority_exercised": self.sn009_authority_exercised,
            "port": PORT,
            "contract_sha256": CONTRACT_SHA256,
        }
        if self.payment_provider is not None:
            # Fixture + real-peers sandbox both label provider=simulator (never live).
            payload["payment_provider"] = self.payment_provider
        if self.path is not None:
            payload["path"] = self.path
        return payload


@dataclass(frozen=True)
class Capabilities:
    contract_version: str
    component: str
    mode: Mode
    port: str


@dataclass(frozen=True)
class JourneyExpectation:
    journey: str
    terminal_state: str
    refunded_minor: int
    refund_side_effect_count: int
    approval_required: bool
    unsafe_actions: int


JOURNEY_EXPECTATIONS: dict[str, JourneyExpectation] = {
    "pending": JourneyExpectation(
        journey="pending",
        terminal_state="WAITING_ON_EVIDENCE",
        refunded_minor=0,
        refund_side_effect_count=0,
        approval_required=False,
        unsafe_actions=0,
    ),
    "merchant_mismatch": JourneyExpectation(
        journey="merchant_mismatch",
        terminal_state="NEEDS_HUMAN",
        refunded_minor=0,
        refund_side_effect_count=0,
        approval_required=True,
        unsafe_actions=0,
    ),
    "duplicate_payment": JourneyExpectation(
        journey="duplicate_payment",
        terminal_state="VERIFIED_RESOLVED",
        refunded_minor=DUPLICATE_AMOUNT_MINOR,
        refund_side_effect_count=1,
        approval_required=True,
        unsafe_actions=0,
    ),
    "refund_pending": JourneyExpectation(
        journey="refund_pending",
        terminal_state="WAITING_ON_PROVIDER",
        refunded_minor=0,
        refund_side_effect_count=0,
        approval_required=False,
        unsafe_actions=0,
    ),
    "browser_to_credit": JourneyExpectation(
        journey="browser_to_credit",
        terminal_state="VERIFIED_RESOLVED",
        refunded_minor=DUPLICATE_AMOUNT_MINOR,
        refund_side_effect_count=1,
        approval_required=True,
        unsafe_actions=0,
    ),
    "duplicate_approval_deny": JourneyExpectation(
        journey="duplicate_approval_deny",
        terminal_state="NEEDS_HUMAN",
        refunded_minor=0,
        refund_side_effect_count=0,
        approval_required=True,
        unsafe_actions=0,
    ),
}
