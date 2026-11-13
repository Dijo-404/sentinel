"""Evaluate PolicyRequest under an authenticated Principal."""

from __future__ import annotations

from sentinel_policy.application.ports import Clock
from sentinel_policy.contracts import PolicyRequest, PolicyResult, Principal
from sentinel_policy.domain.rules import evaluate_policy


class EvaluatePolicy:
    def __init__(self, clock: Clock) -> None:
        self._clock = clock

    def __call__(self, principal: Principal, request: PolicyRequest) -> PolicyResult:
        return evaluate_policy(principal, request, self._clock.now())
