from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from sentinel_finharness.contracts import PeerError

from ._payloads import EVIDENCE_BUNDLE


class ValidEvidence:
    def collect(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        _ = request
        return dict(EVIDENCE_BUNDLE)


class UnavailableEvidence:
    def collect(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        _ = request
        raise PeerError("evidence.v1", "unavailable", "evidence peer not reachable")


class MalformedEvidence:
    def collect(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        _ = request
        return {"case_id": "case-demo-42", "evidence": "not-a-list"}


class UnauthorizedEvidence:
    def collect(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        _ = request
        raise PeerError("evidence.v1", "unauthorized_or_out_of_scope", "tenant scope denied")
