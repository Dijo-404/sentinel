from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from sentinel_finharness.contracts import PeerError

from ._payloads import VERIFICATION_RESULT


class ValidVerifier:
    def assess(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        result = dict(VERIFICATION_RESULT)
        result["action_id"] = request["action_id"]
        result["case_id"] = request["case_id"]
        result["case_revision"] = request["case_revision"]
        return result


class UnavailableVerifier:
    def assess(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        _ = request
        raise PeerError("verifier.v1", "unavailable", "verifier peer not reachable")


class MalformedVerifier:
    def assess(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        _ = request
        return {"assessment_id": "x", "status": "DONE"}


class UnauthorizedVerifier:
    def assess(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        _ = request
        raise PeerError("verifier.v1", "unauthorized_or_out_of_scope", "case outside scope")
