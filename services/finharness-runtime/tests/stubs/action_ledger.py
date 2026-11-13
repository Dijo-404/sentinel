from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from sentinel_finharness_runtime.domain.errors import PeerError

from ._payloads import ACTION_RECORD, DIGEST, REFUND_ACTION, RESERVED_RECORD


class ValidActionLedger:
    def create_proposal(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        _ = request
        return dict(ACTION_RECORD)

    def reserve(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        if not request.get("approval_id"):
            raise PeerError("action-ledger.v1", "unauthorized_or_out_of_scope", "approval required")
        return dict(RESERVED_RECORD)

    def get_action(self, action_id: str) -> Mapping[str, Any]:
        record = dict(ACTION_RECORD)
        record["action_id"] = action_id
        return record

    def query_by_provider_ref(self, provider_ref: str) -> Mapping[str, Any]:
        return {
            "action_id": "action-demo-1",
            "provider_ref": provider_ref,
            "status": "SUBMITTED",
            "payload": REFUND_ACTION,
            "action_digest": DIGEST,
        }


class UnavailableActionLedger:
    def create_proposal(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        _ = request
        raise PeerError("action-ledger.v1", "unavailable", "ledger peer not reachable")

    def reserve(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        _ = request
        raise PeerError("action-ledger.v1", "unavailable", "ledger peer not reachable")

    def get_action(self, action_id: str) -> Mapping[str, Any]:
        _ = action_id
        raise PeerError("action-ledger.v1", "unavailable", "ledger peer not reachable")

    def query_by_provider_ref(self, provider_ref: str) -> Mapping[str, Any]:
        _ = provider_ref
        raise PeerError("action-ledger.v1", "unavailable", "ledger peer not reachable")


class MalformedActionLedger:
    def create_proposal(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        _ = request
        return {"action_id": "action-demo-1"}

    def reserve(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        _ = request
        return {"action_id": "action-demo-1"}

    def get_action(self, action_id: str) -> Mapping[str, Any]:
        _ = action_id
        return {"status": "PROPOSED"}

    def query_by_provider_ref(self, provider_ref: str) -> Mapping[str, Any]:
        _ = provider_ref
        return {"status": "???"}


class UnauthorizedActionLedger:
    def create_proposal(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        _ = request
        raise PeerError(
            "action-ledger.v1",
            "unauthorized_or_out_of_scope",
            "workflow principal out of tenant scope",
        )

    def reserve(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        _ = request
        raise PeerError(
            "action-ledger.v1",
            "unauthorized_or_out_of_scope",
            "approval not authorized for this digest",
        )

    def get_action(self, action_id: str) -> Mapping[str, Any]:
        _ = action_id
        raise PeerError(
            "action-ledger.v1",
            "unauthorized_or_out_of_scope",
            "action outside authenticated scope",
        )

    def query_by_provider_ref(self, provider_ref: str) -> Mapping[str, Any]:
        _ = provider_ref
        raise PeerError(
            "action-ledger.v1",
            "unauthorized_or_out_of_scope",
            "provider_ref outside authenticated scope",
        )
