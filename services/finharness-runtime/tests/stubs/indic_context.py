from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from sentinel_finharness_runtime.domain.errors import PeerError

from ._payloads import MODEL_RESULT


class ValidIndicContext:
    def propose(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        result = dict(MODEL_RESULT)
        result["original_text"] = request["input"]["original_text"]
        result["language"] = request["input"]["language"]
        return result


class UnavailableIndicContext:
    def propose(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        _ = request
        raise PeerError("indic-context.v1", "unavailable", "indic-context peer not reachable")


class MalformedIndicContext:
    def propose(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        _ = request
        return {
            "outcome": "PROPOSAL",
            "reason_codes": [],
            "original_text": "x",
            "language": "en-IN",
        }


class UnauthorizedIndicContext:
    def propose(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        _ = request
        raise PeerError(
            "indic-context.v1",
            "unauthorized_or_out_of_scope",
            "model principal denied for tenant",
        )
