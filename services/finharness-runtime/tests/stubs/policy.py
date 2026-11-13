from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from sentinel_finharness_runtime.domain.errors import PeerError

from ._payloads import POLICY_RESULT


class ValidPolicy:
    def evaluate(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        _ = request
        return dict(POLICY_RESULT)


class UnavailablePolicy:
    def evaluate(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        _ = request
        raise PeerError("policy.v1", "unavailable", "policy peer not reachable")


class MalformedPolicy:
    def evaluate(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        _ = request
        return {"outcome": "MAYBE", "reason_codes": [], "policy_version": "x", "action_digest": "y"}


class UnauthorizedPolicy:
    def evaluate(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        _ = request
        raise PeerError("policy.v1", "unauthorized_or_out_of_scope", "workflow principal denied")
