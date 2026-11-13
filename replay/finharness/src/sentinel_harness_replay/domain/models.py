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
ReplayPath = Literal["recorded", "simulation"]
FaultKind = Literal[
    "commit_then_timeout",
    "timeout_before_commit",
    "duplicate_event",
    "out_of_order_event",
    "delayed_confirmation",
]


@dataclass(frozen=True)
class FixtureEvent:
    at_s: int
    type: str
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class FaultEvent:
    at_s: int
    kind: FaultKind
    provider_ref: str = ""


@dataclass(frozen=True)
class FaultSchedule:
    schedule_id: str
    seed: int
    events: tuple[FaultEvent, ...]


@dataclass(frozen=True)
class ReplayFixture:
    fixture_id: str
    scenario: str
    seed: int
    policy_version: str
    workflow_version: str
    model_version: str
    runtime_version: str
    events: tuple[FixtureEvent, ...]
    fault_schedule: FaultSchedule
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
class WriteOp:
    """One refund write attempted by a candidate (stable reference + amount)."""

    provider_ref: str
    action_id: str
    transaction_ref: str
    amount_minor: int


@dataclass(frozen=True)
class Recording:
    """Frozen recorded responses for deterministic recorded replay."""

    recording_id: str
    seed: int
    write_sequence: tuple[WriteOp, ...]
    terminal_state: str
    refund_side_effect_count: int
    refunded_minor: int
    unsafe_actions: int
    provider_refs: tuple[str, ...]
    side_effects: tuple[SideEffect, ...]


@dataclass(frozen=True)
class CandidatePatch:
    """Immutable candidate change. Only prompt/context/routing fields allowed."""

    candidate_id: str
    prompt_examples: tuple[str, ...] = ()
    context_order: tuple[str, ...] = ()
    localization_templates: tuple[str, ...] = ()
    routing_budget: int = 0
    # Forbidden control-surface fields (must stay empty / unchanged).
    policy_version: str | None = None
    approval_requirement: str | None = None
    auth_roles: tuple[str, ...] | None = None
    provider_mapping: dict[str, str] | None = None
    production_code_path: str | None = None


@dataclass(frozen=True)
class CandidateOutcome:
    candidate_id: str
    terminal_state: str
    refund_side_effect_count: int
    refunded_minor: int
    unsafe_actions: int
    side_effects: tuple[SideEffect, ...]
    provider_refs: tuple[str, ...]
    write_sequence: tuple[WriteOp, ...]
    replay_path: ReplayPath
    quality_score: float
    critical_safety_violations: int
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
class HarnessReplayModes:
    run_mode: RunMode
    seed: int
    model_mode: ModelMode
    production_writes_blocked: bool
    production_notifications_blocked: bool
    live_controls_immutable: bool
    real_runtime_adapter: Literal["absent", "configured"]
    real_finbench_adapter: Literal["absent", "configured"]
    real_replay_adapter: Literal["absent", "configured"]


@dataclass(frozen=True)
class PromotionRecommendation:
    decision: Promotion
    reason_code: str
    baseline_candidate_id: str
    candidate_id: str
    quality_improved: bool
    safety_regression: bool


@dataclass(frozen=True)
class RunReport:
    contract_version: ContractVersion
    run_id: str
    mode: RunMode
    status: RunStatus
    checks: tuple[CheckResult, ...]
    output_artifacts: tuple[ArtifactRef, ...]
    modes: HarnessReplayModes
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
                "live_controls_immutable": self.modes.live_controls_immutable,
                "real_runtime_adapter": self.modes.real_runtime_adapter,
                "real_finbench_adapter": self.modes.real_finbench_adapter,
                "real_replay_adapter": self.modes.real_replay_adapter,
            },
            "promotion": None
            if self.promotion is None
            else {
                "decision": self.promotion.decision,
                "reason_code": self.promotion.reason_code,
                "baseline_candidate_id": self.promotion.baseline_candidate_id,
                "candidate_id": self.promotion.candidate_id,
                "quality_improved": self.promotion.quality_improved,
                "safety_regression": self.promotion.safety_regression,
            },
            "differences": list(self.differences),
        }
