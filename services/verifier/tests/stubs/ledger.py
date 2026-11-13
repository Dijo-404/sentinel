"""action-ledger.v1 local doubles. Reservation authority stays here."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Literal

from sentinel_verifier.domain.errors import PeerError
from sentinel_verifier.domain.types import OutcomeRequest

StubMode = Literal["valid", "unavailable", "malformed", "unauthorized_or_out_of_scope"]


class StubLedger:
    def __init__(self, *, mode: StubMode = "valid") -> None:
        self.mode = mode
        self.actions: dict[str, dict[str, Any]] = {}
        self.outcomes: list[dict[str, Any]] = []
        self.reservations_held: set[str] = set()

    def seed_action(
        self,
        *,
        action_id: str,
        provider_ref: str,
        status: str = "PENDING",
        payload: dict[str, Any] | None = None,
    ) -> None:
        self.actions[action_id] = {
            "action_id": action_id,
            "provider_ref": provider_ref,
            "payload": payload
            or {
                "action": "REQUEST_REFUND",
                "case_id": "case-demo-42",
                "case_revision": 1,
                "transaction_ref": "TXN-B",
                "amount_minor": 150000,
                "currency": "INR",
                "destination": "ORIGINAL_PAYMENT_ROUTE",
                "evidence_ids": ["evidence-payment-b", "evidence-order"],
                "policy_version": "demo-policy-v1",
            },
            "action_digest": "d5ce68ac9b173525d7ed0989eeb374cbb41b0a551f4457f8406d85342e1a8993",
            "status": status,
        }
        if status in {
            "RESERVED",
            "DISPATCHING",
            "PENDING",
            "OUTCOME_UNKNOWN",
            "PROVIDER_CONFIRMED",
            "ESCALATED",
        }:
            self.reservations_held.add(action_id)

    def get_action(self, action_id: str) -> dict[str, Any]:
        self._guard()
        if action_id not in self.actions:
            raise PeerError("NOT_FOUND", "Unknown action", status_code=404)
        return deepcopy(self.actions[action_id])

    def report_outcome(self, action_id: str, outcome: OutcomeRequest) -> dict[str, Any]:
        self._guard()
        if action_id not in self.actions:
            raise PeerError("NOT_FOUND", "Unknown action", status_code=404)
        body = outcome.as_dict()
        record = deepcopy(self.actions[action_id])
        # Duplicate evidence is a no-op for identical target.
        if record["status"] == body["status"]:
            self.outcomes.append({"action_id": action_id, **body, "noop": True})
            return record
        # Never release on unknown/pending; only authoritative final failure.
        if body["status"] == "FAILED_FINAL":
            self.reservations_held.discard(action_id)
        elif body["status"] == "CREDIT_CONFIRMED":
            # Completed path retains completed balance semantics; reservation released.
            self.reservations_held.discard(action_id)
        record["status"] = body["status"]
        record["last_outcome"] = body
        self.actions[action_id] = record
        self.outcomes.append({"action_id": action_id, **body})
        return record

    def reservation_held(self, action_id: str) -> bool:
        return action_id in self.reservations_held

    def _guard(self) -> None:
        if self.mode == "unavailable":
            raise PeerError("PEER_UNAVAILABLE", "Required peer unavailable", status_code=503)
        if self.mode == "malformed":
            raise PeerError("MALFORMED_PEER", "Malformed ledger response", status_code=502)
        if self.mode == "unauthorized_or_out_of_scope":
            raise PeerError("FORBIDDEN", "Unauthorized or out of scope", status_code=403)
