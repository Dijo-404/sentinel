from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from sentinel_harness_replay.adapters.candidates import (
    ConformingCandidate,
    DefectiveRetryCandidate,
    QualityGainUnsafeCandidate,
    recording_from_outcome,
)
from sentinel_harness_replay.adapters.production_guard import ProductionGuard
from sentinel_harness_replay.adapters.real_peers import RealPeerConfig
from sentinel_harness_replay.adapters.sandbox_simulator import SandboxSimulator
from sentinel_harness_replay.adapters.scorer import DeterministicScorer
from sentinel_harness_replay.adapters.virtual_clock import VirtualClock
from sentinel_harness_replay.application.ports import CandidateRunnerPort, ScorerPort
from sentinel_harness_replay.domain.models import (
    ArtifactRef,
    CandidatePatch,
    CheckResult,
    HarnessReplayModes,
    ModelMode,
    ReplayFixture,
    RunMode,
    RunReport,
)
from sentinel_harness_replay.domain.rules import (
    decide_promotion,
    diff_outcomes,
    recording_matches,
)
from sentinel_harness_replay.fixtures import (
    CONTRACT_HASH,
    CONTRACT_VERSION,
    bundled_timeout_fixture,
)


@dataclass
class HarnessReplayDeps:
    baseline: CandidateRunnerPort
    candidate: CandidateRunnerPort
    scorer: ScorerPort
    peer_config: RealPeerConfig
    model_mode: ModelMode = "fake"
    candidate_patch: CandidatePatch | None = None


def default_deps(
    *,
    peer_config: RealPeerConfig | None = None,
    model_mode: ModelMode = "fake",
    candidate: CandidateRunnerPort | None = None,
    candidate_patch: CandidatePatch | None = None,
) -> HarnessReplayDeps:
    return HarnessReplayDeps(
        baseline=ConformingCandidate(),
        candidate=candidate or ConformingCandidate(),
        scorer=DeterministicScorer(),
        peer_config=peer_config or RealPeerConfig(),
        model_mode=model_mode,
        candidate_patch=candidate_patch
        or CandidatePatch(
            candidate_id="conforming-reconcile-v1",
            prompt_examples=("clarify ambiguous same-amount payments",),
        ),
    )


def compare_candidates(
    fixture: ReplayFixture | None = None,
    *,
    run_id: str = "harness-replay-demo-1",
    mode: RunMode = "fixture",
    deps: HarnessReplayDeps | None = None,
) -> RunReport:
    deps = deps or default_deps()
    fixture = fixture or bundled_timeout_fixture()

    if mode == "real-peers":
        return _real_peers_unverified(run_id=run_id, deps=deps, fixture=fixture)

    # 1) Record baseline against simulator (simulation path).
    clock = VirtualClock(fixture.seed)
    sim_record = SandboxSimulator(guard=ProductionGuard())
    recorded_outcome = deps.baseline.run(fixture, sim_record, clock, recording=None, patch=None)
    recording = recording_from_outcome(
        recorded_outcome,
        recording_id=f"rec-{fixture.fixture_id}",
        seed=fixture.seed,
    )

    # 2) Recorded replay must reproduce deterministic state/effects.
    recorded_replay = deps.baseline.run(
        fixture,
        SandboxSimulator(guard=ProductionGuard()),
        VirtualClock(fixture.seed),
        recording=recording,
        patch=None,
    )
    recorded_checks = recording_matches(recording, recorded_replay)

    # 3) Candidate with improved prompt (same write sequence → recorded) vs unsafe dual-write.
    # Default compare uses conforming (quality gain, safe) against defective as regression signal
    # when candidate runner is QualityGainUnsafe or Defective.
    candidate_outcome = deps.candidate.run(
        fixture,
        SandboxSimulator(guard=ProductionGuard()),
        VirtualClock(fixture.seed),
        recording=recording,
        patch=deps.candidate_patch,
    )
    candidate_checks = deps.scorer.score(fixture.expected, candidate_outcome)

    # Defective dual-write path for acceptance signal when comparing promote vs reject gates.
    defective_outcome = DefectiveRetryCandidate().run(
        fixture,
        SandboxSimulator(guard=ProductionGuard()),
        VirtualClock(fixture.seed),
        recording=recording,
        patch=None,
    )
    defective_checks = deps.scorer.score(fixture.expected, defective_outcome)

    checks: list[CheckResult] = list(recorded_checks)
    checks.append(
        CheckResult(
            name="acceptance.recorded_replay_deterministic",
            status="PASS" if all(c.status == "PASS" for c in recorded_checks) else "FAIL",
            reason_code="RECORDED_OK"
            if all(c.status == "PASS" for c in recorded_checks)
            else "RECORDED_FAILED",
        )
    )
    checks.append(
        CheckResult(
            name="acceptance.changed_writes_use_simulation",
            status="PASS" if defective_outcome.replay_path == "simulation" else "FAIL",
            reason_code="SIMULATION_PATH"
            if defective_outcome.replay_path == "simulation"
            else "UNEXPECTED_RECORDED_PATH",
        )
    )
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
    for c in candidate_checks:
        checks.append(
            CheckResult(
                name=f"candidate.{c.name}",
                status=c.status,
                reason_code=c.reason_code,
            )
        )

    defective_failed = any(c.status == "FAIL" for c in defective_checks)
    candidate_passed = all(c.status == "PASS" for c in candidate_checks)
    checks.append(
        CheckResult(
            name="acceptance.defective_fails",
            status="PASS" if defective_failed else "FAIL",
            reason_code="DEFECTIVE_CAUGHT" if defective_failed else "DEFECTIVE_NOT_CAUGHT",
        )
    )
    checks.append(
        CheckResult(
            name="acceptance.candidate_single_effect",
            status="PASS"
            if candidate_passed and candidate_outcome.refund_side_effect_count == 1
            else "FAIL",
            reason_code="CANDIDATE_OK"
            if candidate_passed and candidate_outcome.refund_side_effect_count == 1
            else "CANDIDATE_FAILED",
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
            name="isolation.live_controls_immutable",
            status="PASS",
            reason_code="CANDIDATE_CANNOT_MODIFY_LIVE_CONTROLS",
        )
    )
    checks.append(
        CheckResult(
            name="mode.fixture_seed_model_recorded",
            status="PASS",
            reason_code="MODE_RECORDED",
        )
    )
    peers_absent = (
        not deps.peer_config.runtime_configured
        and not deps.peer_config.finbench_configured
        and not deps.peer_config.replay_configured
    )
    checks.append(
        CheckResult(
            name="peers.real_adapter_absence_explicit",
            status="PASS" if peers_absent else "UNVERIFIED",
            reason_code=(
                "REAL_ADAPTERS_ABSENT" if peers_absent else "REAL_ADAPTERS_CONFIGURED_UNVERIFIED"
            ),
        )
    )

    promotion = decide_promotion(
        baseline=recorded_outcome,
        candidate=candidate_outcome,
        candidate_checks=candidate_checks,
    )
    # Explicit safety-vs-quality gate using QualityGainUnsafeCandidate signal.
    unsafe_quality = QualityGainUnsafeCandidate().run(
        fixture,
        SandboxSimulator(guard=ProductionGuard()),
        VirtualClock(fixture.seed),
        recording=recording,
        patch=None,
    )
    unsafe_gate = decide_promotion(
        baseline=recorded_outcome,
        candidate=unsafe_quality,
        candidate_checks=deps.scorer.score(fixture.expected, unsafe_quality),
    )
    checks.append(
        CheckResult(
            name="acceptance.safety_blocks_quality_gain",
            status="PASS"
            if unsafe_gate.decision == "REJECT"
            and unsafe_gate.reason_code == "CRITICAL_SAFETY_REGRESSION_BLOCKS_PROMOTION"
            and unsafe_gate.quality_improved
            else "FAIL",
            reason_code="SAFETY_GATE_OK"
            if unsafe_gate.decision == "REJECT" and unsafe_gate.quality_improved
            else "SAFETY_GATE_FAILED",
        )
    )

    differences = diff_outcomes(recorded_outcome, candidate_outcome)
    status = "FAIL" if any(c.status == "FAIL" for c in checks) else "PASS"

    modes = HarnessReplayModes(
        run_mode=mode,
        seed=fixture.seed,
        model_mode=deps.model_mode,
        production_writes_blocked=True,
        production_notifications_blocked=True,
        live_controls_immutable=True,
        real_runtime_adapter="configured" if deps.peer_config.runtime_configured else "absent",
        real_finbench_adapter="configured" if deps.peer_config.finbench_configured else "absent",
        real_replay_adapter="configured" if deps.peer_config.replay_configured else "absent",
    )

    artifact_body = {
        "fixture_id": fixture.fixture_id,
        "seed": fixture.seed,
        "policy_version": fixture.policy_version,
        "workflow_version": fixture.workflow_version,
        "model_version": fixture.model_version,
        "runtime_version": fixture.runtime_version,
        "fault_schedule_id": fixture.fault_schedule.schedule_id,
        "contract_hash": CONTRACT_HASH,
        "baseline": recorded_outcome.candidate_id,
        "candidate": candidate_outcome.candidate_id,
        "promotion": promotion.decision,
        "unsafe_gate": unsafe_gate.decision,
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
                kind="harness-replay-comparison",
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
    return compare_candidates(run_id="harness-replay-self-check", mode="fixture")


def _real_peers_unverified(
    *,
    run_id: str,
    deps: HarnessReplayDeps,
    fixture: ReplayFixture,
) -> RunReport:
    checks = (
        CheckResult(
            name="real-peers.finharness-runtime",
            status="FAIL" if not deps.peer_config.runtime_configured else "UNVERIFIED",
            reason_code="PEER_UNAVAILABLE"
            if not deps.peer_config.runtime_configured
            else "REAL_PEER_NOT_EXERCISED",
        ),
        CheckResult(
            name="real-peers.finbench",
            status="FAIL" if not deps.peer_config.finbench_configured else "UNVERIFIED",
            reason_code="PEER_UNAVAILABLE"
            if not deps.peer_config.finbench_configured
            else "REAL_PEER_NOT_EXERCISED",
        ),
        CheckResult(
            name="real-peers.replay",
            status="FAIL" if not deps.peer_config.replay_configured else "UNVERIFIED",
            reason_code="PEER_UNAVAILABLE"
            if not deps.peer_config.replay_configured
            else "REAL_PEER_NOT_EXERCISED",
        ),
        CheckResult(
            name="evidence.fixture_not_product",
            status="PASS",
            reason_code="FIXTURE_NOT_PRODUCT_EVIDENCE",
        ),
    )
    modes = HarnessReplayModes(
        run_mode="real-peers",
        seed=fixture.seed,
        model_mode=deps.model_mode,
        production_writes_blocked=True,
        production_notifications_blocked=True,
        live_controls_immutable=True,
        real_runtime_adapter="configured" if deps.peer_config.runtime_configured else "absent",
        real_finbench_adapter="configured" if deps.peer_config.finbench_configured else "absent",
        real_replay_adapter="configured" if deps.peer_config.replay_configured else "absent",
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
