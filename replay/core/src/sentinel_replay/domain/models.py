from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

ContractVersion = Literal["sentinel.task-contracts.v1"]
RunMode = Literal["fixture", "real-peers"]
ModelMode = Literal["fake", "live", "absent"]
CheckStatus = Literal["PASS", "FAIL", "UNVERIFIED"]
RunStatus = Literal["PASS", "FAIL", "UNVERIFIED"]
EvidenceMode = Literal["fixture", "real-component", "live-provider"]
Promotion = Literal["PROMOTE", "REJECT", "HOLD"]


@dataclass(frozen=True)
class FixtureEvent:
    at_s: int
    type: str
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ReplayFixture:
    fixture_id: str
    scenario: str
    seed: int
    policy_version: str
    workflow_version: str
    model_version: str
    events: tuple[FixtureEvent, ...]
    expected: dict[str, Any]
    refund: dict[str, Any]


@dataclass(frozen=True)
class SideEffect:
    kind: str
    provider_ref: str
    transaction_ref: str
    amount_minor: int
    route: str


@dataclass(frozen=True)
class CandidateOutcome:
    candidate_id: str
    terminal_state: str
    refund_side_effect_count: int
    refunded_minor: int
    unsafe_actions: int
    side_effects: tuple[SideEffect, ...]
    provider_refs: tuple[str, ...]
    notes: tuple[str, ...] = ()


@dataclass(frozen=True)
class CheckResult:
    name: str
    status: CheckStatus
    reason_code: str


@dataclass(frozen=True)
class ArtifactRef:
    kind: str
    uri: str
    sha256: str
    component_version: str
    evidence_mode: EvidenceMode


@dataclass(frozen=True)
class ReplayModes:
    run_mode: RunMode
    seed: int
    model_mode: ModelMode
    production_writes_blocked: bool
    production_notifications_blocked: bool
    real_evaluation_adapter: Literal["absent", "configured"]
    real_payment_provider_adapter: Literal["absent", "configured"]


@dataclass(frozen=True)
class PromotionRecommendation:
    decision: Promotion
    reason_code: str
    conforming_candidate_id: str
    defective_candidate_id: str


@dataclass(frozen=True)
class RunReport:
    contract_version: ContractVersion
    run_id: str
    mode: RunMode
    status: RunStatus
    checks: tuple[CheckResult, ...]
    output_artifacts: tuple[ArtifactRef, ...]
    modes: ReplayModes
    promotion: PromotionRecommendation | None
    differences: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "run_id": self.run_id,
            "mode": self.mode,
            "status": self.status,
            "checks": [
                {"name": c.name, "status": c.status, "reason_code": c.reason_code}
                for c in self.checks
            ],
            "output_artifacts": [
                {
                    "kind": a.kind,
                    "uri": a.uri,
                    "sha256": a.sha256,
                    "component_version": a.component_version,
                    "evidence_mode": a.evidence_mode,
                }
                for a in self.output_artifacts
            ],
            "modes": {
                "run_mode": self.modes.run_mode,
                "seed": self.modes.seed,
                "model_mode": self.modes.model_mode,
                "production_writes_blocked": self.modes.production_writes_blocked,
                "production_notifications_blocked": self.modes.production_notifications_blocked,
                "real_evaluation_adapter": self.modes.real_evaluation_adapter,
                "real_payment_provider_adapter": self.modes.real_payment_provider_adapter,
            },
            "promotion": None
            if self.promotion is None
            else {
                "decision": self.promotion.decision,
                "reason_code": self.promotion.reason_code,
                "conforming_candidate_id": self.promotion.conforming_candidate_id,
                "defective_candidate_id": self.promotion.defective_candidate_id,
            },
            "differences": list(self.differences),
        }
