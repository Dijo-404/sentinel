"""action-ledger.v1 local doubles. Reservation authority stays here."""

from __future__ import annotations

from collections.abc import Sequence
from copy import deepcopy
from typing import Any, Literal

from sentinel_dispatcher.domain.types import Command, OutcomeRequest, PeerError

StubMode = Literal["valid", "unavailable", "malformed", "unauthorized_or_out_of_scope"]


class StubLedger:
    def __init__(
        self,
        commands: Sequence[Command] | None = None,
        *,
        mode: StubMode = "valid",
        tenant_id: str = "tenant-demo",
    ) -> None:
        self.mode = mode
        self.tenant_id = tenant_id
        self._queue = list(commands or [])
        self.outcomes: list[dict[str, Any]] = []
        self.actions: dict[str, dict[str, Any]] = {}
        self.reservations_held: set[str] = set()
        for command in self._queue:
            self.reservations_held.add(command.action_id)
            self.actions[command.action_id] = {
                "action_id": command.action_id,
                "provider_ref": command.provider_ref,
                "payload": dict(command.payload),
                "action_digest": command.action_digest,
                "status": "DISPATCHING",
            }

    def enqueue(self, command: Command) -> None:
        self._queue.append(command)
        self.reservations_held.add(command.action_id)
        self.actions[command.action_id] = {
            "action_id": command.action_id,
            "provider_ref": command.provider_ref,
            "payload": dict(command.payload),
            "action_digest": command.action_digest,
            "status": "DISPATCHING",
        }

    def claim(self, *, limit: int) -> Sequence[Command]:
        self._guard()
        if limit < 1 or limit > 100:
            raise PeerError("INVALID_LIMIT", "limit must be 1..100", status_code=422)
        claimed = self._queue[:limit]
        self._queue = self._queue[limit:]
        return list(claimed)

    def report_outcome(self, action_id: str, outcome: OutcomeRequest) -> dict:
        self._guard()
        if action_id not in self.actions:
            raise PeerError("NOT_FOUND", "Unknown action", status_code=404)
        body = outcome.as_dict()
        record = deepcopy(self.actions[action_id])
        # Authoritative final failure alone may release; never lease expiry.
        if body["status"] == "FAILED_FINAL" and body.get("reason_code") == "PROVIDER_FAILED_FINAL":
            self.reservations_held.discard(action_id)
        record["status"] = body["status"]
        record["last_outcome"] = body
        self.actions[action_id] = record
        self.outcomes.append({"action_id": action_id, **body})
        return record

    def get_action(self, action_id: str) -> dict:
        self._guard()
        if action_id not in self.actions:
            raise PeerError("NOT_FOUND", "Unknown action", status_code=404)
        return deepcopy(self.actions[action_id])

    def reservation_held(self, action_id: str) -> bool:
        return action_id in self.reservations_held

    def _guard(self) -> None:
        if self.mode == "unavailable":
            raise PeerError("PEER_UNAVAILABLE", "Required peer unavailable", status_code=503)
        if self.mode == "malformed":
            raise PeerError("MALFORMED_PEER", "Malformed ledger response", status_code=502)
        if self.mode == "unauthorized_or_out_of_scope":
            raise PeerError("FORBIDDEN", "Unauthorized or out of scope", status_code=403)
