from __future__ import annotations

from typing import Protocol

from sentinel_replay.domain.models import (
    CandidateOutcome,
    CheckResult,
    ReplayFixture,
    SideEffect,
)


class VirtualClockPort(Protocol):
    def now_s(self) -> int: ...

    def advance_to(self, at_s: int) -> None: ...

    def reset(self, seed: int) -> None: ...


class SimulatorPort(Protocol):
    """Injected sandbox payment-provider surface used during counterfactual replay."""

    def reset(self, *, seed: int) -> None: ...

    def request_refund(
        self,
        *,
        provider_ref: str,
        action_id: str,
        transaction_ref: str,
        amount_minor: int,
        currency: str = "INR",
        destination: str = "ORIGINAL_PAYMENT_ROUTE",
    ) -> dict: ...

    def lookup_refund(self, provider_ref: str) -> dict | None: ...

    def confirm_provider(self, provider_ref: str) -> dict: ...

    def confirm_credit(self, provider_ref: str) -> dict: ...

    def side_effects(self) -> tuple[SideEffect, ...]: ...

    def refund_side_effect_count(self) -> int: ...


class CandidateRunnerPort(Protocol):
    candidate_id: str

    def run(
        self,
        fixture: ReplayFixture,
        simulator: SimulatorPort,
        clock: VirtualClockPort,
    ) -> CandidateOutcome: ...


class ScorerPort(Protocol):
    def score(self, expected: dict, observed: CandidateOutcome) -> tuple[CheckResult, ...]: ...


class EvaluationPort(Protocol):
    """Consumed evaluation.v1 peer (stubbed locally; real adapter must fail closed)."""

    def capabilities(self) -> dict: ...

    def score_suite(self, report_payload: dict) -> dict: ...


class PaymentProviderPort(Protocol):
    """Consumed payment-provider.v1 peer (stubbed locally; real adapter must fail closed)."""

    def capabilities(self) -> dict: ...

    def get_transactions(self, order_reference: str) -> dict: ...

    def create_refund(self, body: dict, idempotency_key: str) -> dict: ...
