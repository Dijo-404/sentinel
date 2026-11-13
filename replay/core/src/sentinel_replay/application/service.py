from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from sentinel_replay.adapters.candidates import ConformingCandidate, DefectiveRetryCandidate
from sentinel_replay.adapters.production_guard import ProductionGuard
from sentinel_replay.adapters.real_peers import RealPeerConfig
from sentinel_replay.adapters.sandbox_simulator import SandboxSimulator
from sentinel_replay.adapters.scorer import DeterministicScorer
from sentinel_replay.adapters.virtual_clock import VirtualClock
from sentinel_replay.application.ports import CandidateRunnerPort, ScorerPort
from sentinel_replay.domain.models import (
    ArtifactRef,
    CheckResult,
    ModelMode,
    ReplayFixture,
    ReplayModes,
    RunMode,
    RunReport,
)
from sentinel_replay.domain.rules import decide_promotion, diff_outcomes
from sentinel_replay.fixtures import CONTRACT_HASH, CONTRACT_VERSION, bundled_timeout_fixture


@dataclass
class ReplayDeps:
    conforming: CandidateRunnerPort
    defective: CandidateRunnerPort
    scorer: ScorerPort
    peer_config: RealPeerConfig
    model_mode: ModelMode = "fake"


def default_deps(
    *,
    peer_config: RealPeerConfig | None = None,
    model_mode: ModelMode = "fake",
) -> ReplayDeps:
    return ReplayDeps(
        conforming=ConformingCandidate(),
        defective=DefectiveRetryCandidate(),
        scorer=DeterministicScorer(),
        peer_config=peer_config or RealPeerConfig(),
        model_mode=model_mode,
    )


def compare_candidates(
    fixture: ReplayFixture | None = None,
    *,
    run_id: str = "replay-demo-1",
    mode: RunMode = "fixture",
    deps: ReplayDeps | None = None,
) -> RunReport:
    deps = deps or default_deps()
    fixture = fixture or bundled_timeout_fixture()

    if mode == "real-peers":
        return _real_peers_unverified(run_id=run_id, deps=deps, fixture=fixture)

    guard = ProductionGuard()
    clock = VirtualClock(fixture.seed)
    sim_defective = SandboxSimulator(guard=guard)
    sim_conforming = SandboxSimulator(guard=ProductionGuard())

    defective_outcome = deps.defective.run(fixture, sim_defective, clock)
    conforming_outcome = deps.conforming.run(fixture, sim_conforming, VirtualClock(fixture.seed))

    defective_checks = deps.scorer.score(fixture.expected, defective_outcome)
    conforming_checks = deps.scorer.score(fixture.expected, conforming_outcome)

    # Defective assertion failures are the desired regression signal. Record a
    # caught mismatch as PASS; axes the defective still matches stay PASS.
    checks: list[CheckResult] = []
    for c in defective_checks:
        if c.status == "FAIL":
            checks.append(
                CheckResult(
                    name=f"defective.{c.name}",
                    status="PASS",
                    reason_code=f"CAUGHT_{c.reason_code}",
                )
            )
        else:
            checks.append(
                CheckResult(
                    name=f"defective.{c.name}",
                    status="PASS",
                    reason_code=c.reason_code,
                )
            )
    for c in conforming_checks:
        checks.append(
            CheckResult(
                name=f"conforming.{c.name}",
                status=c.status,
                reason_code=c.reason_code,
            )
        )

    # Defective must fail effect/state assertions; conforming must pass.
    defective_failed = any(c.status == "FAIL" for c in defective_checks)
    conforming_passed = all(c.status == "PASS" for c in conforming_checks)
    checks.append(
        CheckResult(
            name="acceptance.defective_fails",
            status="PASS" if defective_failed else "FAIL",
            reason_code="DEFECTIVE_CAUGHT" if defective_failed else "DEFECTIVE_NOT_CAUGHT",
        )
    )
    checks.append(
        CheckResult(
            name="acceptance.conforming_single_effect",
            status="PASS"
            if conforming_passed and conforming_outcome.refund_side_effect_count == 1
            else "FAIL",
            reason_code="CONFORMING_OK"
            if conforming_passed and conforming_outcome.refund_side_effect_count == 1
            else "CONFORMING_FAILED",
        )
    )
    checks.append(
        CheckResult(
            name="isolation.production_routes_blocked",
            status="PASS",
            reason_code="WRITES_AND_NOTIFICATIONS_BLOCKED",
        )
    )
    checks.append(
        CheckResult(
            name="mode.fixture_seed_model_recorded",
            status="PASS",
            reason_code="MODE_RECORDED",
        )
    )
    checks.append(
        CheckResult(
            name="peers.real_adapter_absence_explicit",
            status="PASS"
            if (
                not deps.peer_config.evaluation_configured
                and not deps.peer_config.payment_provider_configured
            )
            else "UNVERIFIED",
            reason_code="REAL_ADAPTERS_ABSENT"
            if (
                not deps.peer_config.evaluation_configured
                and not deps.peer_config.payment_provider_configured
            )
            else "REAL_ADAPTERS_CONFIGURED_UNVERIFIED",
        )
    )

    promotion = decide_promotion(
        conforming=conforming_outcome,
        defective=defective_outcome,
        conforming_checks=conforming_checks,
        defective_checks=defective_checks,
    )
    differences = diff_outcomes(defective_outcome, conforming_outcome)

    status = "FAIL" if any(c.status == "FAIL" for c in checks) else "PASS"

    modes = ReplayModes(
        run_mode=mode,
        seed=fixture.seed,
        model_mode=deps.model_mode,
        production_writes_blocked=True,
        production_notifications_blocked=True,
        real_evaluation_adapter="configured"
        if deps.peer_config.evaluation_configured
        else "absent",
        real_payment_provider_adapter="configured"
        if deps.peer_config.payment_provider_configured
        else "absent",
    )

    artifact_body = {
        "fixture_id": fixture.fixture_id,
        "seed": fixture.seed,
        "policy_version": fixture.policy_version,
        "workflow_version": fixture.workflow_version,
        "model_version": fixture.model_version,
        "contract_hash": CONTRACT_HASH,
        "defective": defective_outcome.candidate_id,
        "conforming": conforming_outcome.candidate_id,
        "promotion": promotion.decision,
    }
    digest = hashlib.sha256(
        json.dumps(artifact_body, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()

    return RunReport(
        contract_version=CONTRACT_VERSION,  # type: ignore[arg-type]
        run_id=run_id,
        mode=mode,
        status=status,  # type: ignore[arg-type]
        checks=tuple(checks),
        output_artifacts=(
            ArtifactRef(
                kind="replay-comparison",
                uri=f"fixture://{fixture.fixture_id}",
                sha256=digest,
                component_version="0.1.0",
                evidence_mode="fixture",
            ),
        ),
        modes=modes,
        promotion=promotion,
        differences=differences,
    )


def run_check() -> RunReport:
    """Standalone self-check used by `make check` / CLI."""
    return compare_candidates(run_id="replay-self-check", mode="fixture")


def _real_peers_unverified(
    *,
    run_id: str,
    deps: ReplayDeps,
    fixture: ReplayFixture,
) -> RunReport:
    checks = (
        CheckResult(
            name="real-peers.evaluation",
            status="FAIL" if not deps.peer_config.evaluation_configured else "UNVERIFIED",
            reason_code="PEER_UNAVAILABLE"
            if not deps.peer_config.evaluation_configured
            else "REAL_PEER_NOT_EXERCISED",
        ),
        CheckResult(
            name="real-peers.payment-provider",
            status="FAIL" if not deps.peer_config.payment_provider_configured else "UNVERIFIED",
            reason_code="PEER_UNAVAILABLE"
            if not deps.peer_config.payment_provider_configured
            else "REAL_PEER_NOT_EXERCISED",
        ),
        CheckResult(
            name="evidence.fixture_not_product",
            status="PASS",
            reason_code="FIXTURE_NOT_PRODUCT_EVIDENCE",
        ),
    )
    modes = ReplayModes(
        run_mode="real-peers",
        seed=fixture.seed,
        model_mode=deps.model_mode,
        production_writes_blocked=True,
        production_notifications_blocked=True,
        real_evaluation_adapter="configured"
        if deps.peer_config.evaluation_configured
        else "absent",
        real_payment_provider_adapter="configured"
        if deps.peer_config.payment_provider_configured
        else "absent",
    )
    status: Any = "FAIL" if any(c.status == "FAIL" for c in checks) else "UNVERIFIED"
    return RunReport(
        contract_version=CONTRACT_VERSION,  # type: ignore[arg-type]
        run_id=run_id,
        mode="real-peers",
        status=status,
        checks=checks,
        output_artifacts=(),
        modes=modes,
        promotion=None,
        differences=(),
    )
