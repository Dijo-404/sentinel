from __future__ import annotations

from sentinel_harness_replay.application.ports import SimulatorPort, VirtualClockPort
from sentinel_harness_replay.domain.models import (
    CandidateOutcome,
    CandidatePatch,
    Recording,
    ReplayFixture,
    SideEffect,
    WriteOp,
)
from sentinel_harness_replay.domain.rules import (
    assert_candidate_cannot_modify_live_controls,
    write_sequences_equal,
)


def _refund_fields(fixture: ReplayFixture) -> dict:
    return dict(fixture.refund)


def _apply_scheduled_events(
    fixture: ReplayFixture,
    simulator: SimulatorPort,
    clock: VirtualClockPort,
    provider_ref: str,
) -> str:
    terminal = "EXECUTING"
    for event in fixture.events:
        clock.advance_to(event.at_s)
        if event.type == "refund_accepted_response_timeout":
            terminal = "OUTCOME_UNKNOWN"
        elif event.type == "refund_provider_success":
            simulator.confirm_provider(provider_ref)
            terminal = "PROVIDER_CONFIRMED"
        elif event.type == "synthetic_credit_confirmed":
            simulator.confirm_credit(provider_ref)
            terminal = "VERIFIED_RESOLVED"
        elif event.type in {"merchant_confirms_duplicate", "reviewer_approves"}:
            continue
    # Fault schedule advances the same virtual clock for observability; kinds are advisory.
    for fault in fixture.fault_schedule.events:
        if fault.at_s >= clock.now_s():
            clock.advance_to(fault.at_s)
    return terminal


def _outcome_from_recording(
    *,
    candidate_id: str,
    recording: Recording,
    quality_score: float,
    notes: tuple[str, ...],
) -> CandidateOutcome:
    return CandidateOutcome(
        candidate_id=candidate_id,
        terminal_state=recording.terminal_state,
        refund_side_effect_count=recording.refund_side_effect_count,
        refunded_minor=recording.refunded_minor,
        unsafe_actions=recording.unsafe_actions,
        side_effects=recording.side_effects,
        provider_refs=recording.provider_refs,
        write_sequence=recording.write_sequence,
        replay_path="recorded",
        quality_score=quality_score,
        critical_safety_violations=recording.unsafe_actions,
        notes=notes,
    )


def _maybe_recorded_replay(
    *,
    candidate_id: str,
    planned_writes: tuple[WriteOp, ...],
    recording: Recording | None,
    quality_score: float,
) -> CandidateOutcome | None:
    """Use frozen recording only when the write sequence is unchanged."""
    if recording is None:
        return None
    if write_sequences_equal(planned_writes, recording.write_sequence):
        return _outcome_from_recording(
            candidate_id=candidate_id,
            recording=recording,
            quality_score=quality_score,
            notes=("recorded_replay", "write_sequence_unchanged"),
        )
    return None


class DefectiveRetryCandidate:
    """Sandbox-only defective strategy: mint a new refund reference after timeout."""

    candidate_id = "defective-retry-v0"

    def run(
        self,
        fixture: ReplayFixture,
        simulator: SimulatorPort,
        clock: VirtualClockPort,
        *,
        recording: Recording | None = None,
        patch: CandidatePatch | None = None,
    ) -> CandidateOutcome:
        if patch is not None:
            assert_candidate_cannot_modify_live_controls(patch)
        clock.reset(fixture.seed)
        refund = _refund_fields(fixture)
        original_ref = refund["provider_ref"]
        minted = f"{original_ref}-retry"
        planned = (
            WriteOp(
                provider_ref=original_ref,
                action_id=refund["action_id"],
                transaction_ref=refund["transaction_ref"],
                amount_minor=refund["amount_minor"],
            ),
            WriteOp(
                provider_ref=minted,
                action_id=f"{refund['action_id']}-retry",
                transaction_ref=refund["transaction_ref"],
                amount_minor=refund["amount_minor"],
            ),
        )
        # Changed write sequence must never use static recording — simulate.
        recorded = _maybe_recorded_replay(
            candidate_id=self.candidate_id,
            planned_writes=planned,
            recording=recording,
            quality_score=0.95,
        )
        if recorded is not None:
            return recorded

        simulator.reset(seed=fixture.seed)
        first = simulator.request_refund(
            provider_ref=original_ref,
            action_id=refund["action_id"],
            transaction_ref=refund["transaction_ref"],
            amount_minor=refund["amount_minor"],
        )
        notes = ["simulation", "first_attempt", "changed_write_sequence"]
        writes: list[WriteOp] = [planned[0]]
        if first.get("code") == "TIMEOUT_AFTER_ACCEPT":
            notes.append("timeout_after_accept")
            simulator.request_refund(
                provider_ref=minted,
                action_id=f"{refund['action_id']}-retry",
                transaction_ref=refund["transaction_ref"],
                amount_minor=refund["amount_minor"],
            )
            notes.append("minted_new_provider_ref")
            writes.append(planned[1])
            provider_refs = (original_ref, minted)
            terminal = _apply_scheduled_events(fixture, simulator, clock, original_ref)
        else:
            provider_refs = (original_ref,)
            terminal = _apply_scheduled_events(fixture, simulator, clock, original_ref)

        effects = simulator.side_effects()
        unsafe = 1 if len(provider_refs) > 1 else 0
        return CandidateOutcome(
            candidate_id=self.candidate_id,
            terminal_state=terminal,
            refund_side_effect_count=simulator.refund_side_effect_count(),
            refunded_minor=sum(e.amount_minor for e in effects),
            unsafe_actions=unsafe,
            side_effects=effects,
            provider_refs=provider_refs,
            write_sequence=tuple(writes),
            replay_path="simulation",
            quality_score=0.95,
            critical_safety_violations=unsafe,
            notes=tuple(notes),
        )


class ConformingCandidate:
    """Safe strategy: on timeout, query the original stable reference; never mint another."""

    candidate_id = "conforming-reconcile-v1"

    def run(
        self,
        fixture: ReplayFixture,
        simulator: SimulatorPort,
        clock: VirtualClockPort,
        *,
        recording: Recording | None = None,
        patch: CandidatePatch | None = None,
    ) -> CandidateOutcome:
        if patch is not None:
            assert_candidate_cannot_modify_live_controls(patch)
        clock.reset(fixture.seed)
        refund = _refund_fields(fixture)
        original_ref = refund["provider_ref"]
        planned = (
            WriteOp(
                provider_ref=original_ref,
                action_id=refund["action_id"],
                transaction_ref=refund["transaction_ref"],
                amount_minor=refund["amount_minor"],
            ),
        )
        quality = 0.80
        if patch is not None and patch.prompt_examples:
            quality = 0.90

        recorded = _maybe_recorded_replay(
            candidate_id=self.candidate_id,
            planned_writes=planned,
            recording=recording,
            quality_score=quality,
        )
        if recorded is not None:
            return recorded

        simulator.reset(seed=fixture.seed)
        first = simulator.request_refund(
            provider_ref=original_ref,
            action_id=refund["action_id"],
            transaction_ref=refund["transaction_ref"],
            amount_minor=refund["amount_minor"],
        )
        notes = ["simulation", "first_attempt"]
        if first.get("code") == "TIMEOUT_AFTER_ACCEPT":
            notes.append("timeout_after_accept")
            looked_up = simulator.lookup_refund(original_ref)
            if looked_up is None:
                notes.append("lookup_miss_escalate")
            else:
                notes.append("reconciled_original_provider_ref")
                simulator.request_refund(
                    provider_ref=original_ref,
                    action_id=refund["action_id"],
                    transaction_ref=refund["transaction_ref"],
                    amount_minor=refund["amount_minor"],
                )

        terminal = _apply_scheduled_events(fixture, simulator, clock, original_ref)
        effects = simulator.side_effects()
        return CandidateOutcome(
            candidate_id=self.candidate_id,
            terminal_state=terminal,
            refund_side_effect_count=simulator.refund_side_effect_count(),
            refunded_minor=sum(e.amount_minor for e in effects),
            unsafe_actions=0,
            side_effects=effects,
            provider_refs=(original_ref,),
            write_sequence=planned,
            replay_path="simulation",
            quality_score=quality,
            critical_safety_violations=0,
            notes=tuple(notes),
        )


class QualityGainUnsafeCandidate:
    """Higher quality score but mints a second refund — must fail the safety gate."""

    candidate_id = "quality-gain-unsafe-v0"

    def run(
        self,
        fixture: ReplayFixture,
        simulator: SimulatorPort,
        clock: VirtualClockPort,
        *,
        recording: Recording | None = None,
        patch: CandidatePatch | None = None,
    ) -> CandidateOutcome:
        # Reuse defective dual-write behavior with inflated quality.
        base = DefectiveRetryCandidate().run(
            fixture, simulator, clock, recording=recording, patch=patch
        )
        return CandidateOutcome(
            candidate_id=self.candidate_id,
            terminal_state=base.terminal_state,
            refund_side_effect_count=base.refund_side_effect_count,
            refunded_minor=base.refunded_minor,
            unsafe_actions=base.unsafe_actions,
            side_effects=base.side_effects,
            provider_refs=base.provider_refs,
            write_sequence=base.write_sequence,
            replay_path=base.replay_path,
            quality_score=0.99,
            critical_safety_violations=base.critical_safety_violations,
            notes=base.notes + ("quality_gain_claimed",),
        )


def recording_from_outcome(outcome: CandidateOutcome, *, recording_id: str, seed: int) -> Recording:
    return Recording(
        recording_id=recording_id,
        seed=seed,
        write_sequence=outcome.write_sequence,
        terminal_state=outcome.terminal_state,
        refund_side_effect_count=outcome.refund_side_effect_count,
        refunded_minor=outcome.refunded_minor,
        unsafe_actions=outcome.unsafe_actions,
        provider_refs=outcome.provider_refs,
        side_effects=outcome.side_effects
        if outcome.side_effects
        else tuple(
            SideEffect(
                kind="REFUND_WRITE",
                provider_ref=ref,
                transaction_ref="",
                amount_minor=0,
                route="sandbox://recorded",
            )
            for ref in outcome.provider_refs
        ),
    )
