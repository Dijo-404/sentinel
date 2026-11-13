from __future__ import annotations

from sentinel_replay.application.ports import SimulatorPort, VirtualClockPort
from sentinel_replay.domain.models import CandidateOutcome, ReplayFixture


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
    return terminal


class DefectiveRetryCandidate:
    """Sandbox-only defective strategy: mint a new refund reference after timeout."""

    candidate_id = "defective-retry-v0"

    def run(
        self,
        fixture: ReplayFixture,
        simulator: SimulatorPort,
        clock: VirtualClockPort,
    ) -> CandidateOutcome:
        clock.reset(fixture.seed)
        simulator.reset(seed=fixture.seed)
        refund = _refund_fields(fixture)
        original_ref = refund["provider_ref"]

        first = simulator.request_refund(
            provider_ref=original_ref,
            action_id=refund["action_id"],
            transaction_ref=refund["transaction_ref"],
            amount_minor=refund["amount_minor"],
        )
        notes = ["first_attempt"]
        if first.get("code") == "TIMEOUT_AFTER_ACCEPT":
            notes.append("timeout_after_accept")
            # Defective: mint a new refund ID instead of reconciling the original.
            minted = f"{original_ref}-retry"
            simulator.request_refund(
                provider_ref=minted,
                action_id=f"{refund['action_id']}-retry",
                transaction_ref=refund["transaction_ref"],
                amount_minor=refund["amount_minor"],
            )
            notes.append("minted_new_provider_ref")
            provider_refs = (original_ref, minted)
            # Keep advancing world against the original only; dual effects already recorded.
            terminal = _apply_scheduled_events(fixture, simulator, clock, original_ref)
        else:
            provider_refs = (original_ref,)
            terminal = _apply_scheduled_events(fixture, simulator, clock, original_ref)

        effects = simulator.side_effects()
        return CandidateOutcome(
            candidate_id=self.candidate_id,
            terminal_state=terminal,
            refund_side_effect_count=simulator.refund_side_effect_count(),
            refunded_minor=sum(e.amount_minor for e in effects),
            unsafe_actions=1 if len(provider_refs) > 1 else 0,
            side_effects=effects,
            provider_refs=provider_refs,
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
    ) -> CandidateOutcome:
        clock.reset(fixture.seed)
        simulator.reset(seed=fixture.seed)
        refund = _refund_fields(fixture)
        original_ref = refund["provider_ref"]

        first = simulator.request_refund(
            provider_ref=original_ref,
            action_id=refund["action_id"],
            transaction_ref=refund["transaction_ref"],
            amount_minor=refund["amount_minor"],
        )
        notes = ["first_attempt"]
        if first.get("code") == "TIMEOUT_AFTER_ACCEPT":
            notes.append("timeout_after_accept")
            looked_up = simulator.lookup_refund(original_ref)
            if looked_up is None:
                notes.append("lookup_miss_escalate")
            else:
                notes.append("reconciled_original_provider_ref")
                # Idempotent retry with the same key — no second side effect.
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
            notes=tuple(notes),
        )
