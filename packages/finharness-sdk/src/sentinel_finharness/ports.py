"""Injectable peer protocols. Implementations live outside this SDK or in test stubs."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class EvidencePort(Protocol):
    def collect(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        """evidence.v1 POST /v1/evidence/collect → EvidenceBundle."""


@runtime_checkable
class PolicyPort(Protocol):
    def evaluate(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        """policy.v1 POST /v1/evaluate → PolicyResult."""


@runtime_checkable
class ActionLedgerPort(Protocol):
    def create_proposal(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        """action-ledger.v1 POST /v1/actions/proposals → ActionRecord."""

    def reserve(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        """action-ledger.v1 POST /v1/actions/reservations → ActionRecord."""

    def get_action(self, action_id: str) -> Mapping[str, Any]:
        """action-ledger.v1 GET /v1/actions/{action_id} → ActionRecord."""


@runtime_checkable
class VerifierPort(Protocol):
    def assess(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        """verifier.v1 POST /v1/assessments → VerificationResult."""


@runtime_checkable
class IndicContextPort(Protocol):
    def propose(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        """indic-context.v1 POST /v1/proposals → ModelResult."""


@runtime_checkable
class NotificationPort(Protocol):
    def enqueue(self, *, channel: str, message_code: str) -> Mapping[str, str]:
        """Enqueue a non-financial notification. Must persist or refuse — never fake queued."""
