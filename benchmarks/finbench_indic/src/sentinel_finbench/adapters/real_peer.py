"""Real-peer adapters for finharness-runtime.v1 and indic-context.v1.

Never silently falls back to fixture success when a peer is missing or bad.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from sentinel_finbench.contracts import CONTRACT_VERSION, PeerError


def _fetch(endpoint: str, *, timeout_s: float = 5.0) -> str:
    if not endpoint:
        raise PeerError("peer", "PEER_UNAVAILABLE", "endpoint not configured")
    if endpoint.startswith("file:") or "://" not in endpoint:
        path = Path(endpoint.removeprefix("file://"))
        if not path.is_file():
            raise PeerError("peer", "PEER_UNAVAILABLE", f"file missing: {path}")
        return path.read_text(encoding="utf-8")
    req = Request(endpoint, headers={"Accept": "application/json"})
    try:
        with urlopen(req, timeout=timeout_s) as resp:  # noqa: S310 — operator-configured
            status = getattr(resp, "status", 200)
            if status in {401, 403}:
                raise PeerError("peer", "FORBIDDEN", "unauthorized")
            return resp.read().decode("utf-8")
    except PeerError:
        raise
    except (OSError, URLError, HTTPError, TimeoutError) as exc:
        raise PeerError("peer", "PEER_UNAVAILABLE", f"unavailable: {exc}") from exc


def _parse_json(raw: str, peer: str) -> Mapping[str, Any]:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise PeerError(peer, "MALFORMED", f"malformed JSON: {exc}") from exc
    if not isinstance(data, Mapping):
        raise PeerError(peer, "MALFORMED", "response must be an object")
    return data


class RealRuntimePeer:
    """Loads a finharness-runtime.v1 RunReport (or error) from a configured endpoint."""

    def __init__(self, endpoint: str, *, timeout_s: float = 5.0) -> None:
        self.endpoint = endpoint
        self.timeout_s = timeout_s
        self.peer = "finharness-runtime.v1"

    def capabilities(self) -> Mapping[str, Any]:
        data = self._load()
        if data.get("code") in {"FORBIDDEN", "UNAUTHORIZED", "OUT_OF_SCOPE"}:
            raise PeerError(
                self.peer,
                "unauthorized_or_out_of_scope",
                str(data.get("message", "unauthorized")),
                request_id=str(data.get("request_id", "request-peer-1")),
            )
        caps = data.get("capabilities") if "capabilities" in data else data
        if not isinstance(caps, Mapping):
            raise PeerError(self.peer, "MALFORMED", "capabilities missing")
        if caps.get("contract_version") != CONTRACT_VERSION:
            raise PeerError(self.peer, "INCOMPATIBLE_CONTRACT", "contract_version mismatch")
        if caps.get("component") not in {None, "finharness-runtime", "finharness-runtime.v1"}:
            # Accept either component naming from peers.
            if caps.get("component") and "finharness" not in str(caps.get("component")):
                raise PeerError(self.peer, "INCOMPATIBLE_CONTRACT", "unexpected component")
        return dict(caps)

    def run(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        _ = request
        data = self._load()
        if data.get("code") in {"FORBIDDEN", "UNAUTHORIZED", "OUT_OF_SCOPE"}:
            raise PeerError(
                self.peer,
                "unauthorized_or_out_of_scope",
                str(data.get("message", "unauthorized")),
                request_id=str(data.get("request_id", "request-peer-1")),
            )
        if data.get("code") == "PEER_UNAVAILABLE":
            raise PeerError(self.peer, "unavailable", str(data.get("message", "unavailable")))
        if data.get("contract_version") != CONTRACT_VERSION:
            raise PeerError(self.peer, "MALFORMED", "missing or incompatible contract_version")
        if data.get("status") not in {"PASS", "FAIL", "UNVERIFIED"}:
            raise PeerError(self.peer, "MALFORMED", "RunReport.status missing")
        return dict(data)

    def _load(self) -> Mapping[str, Any]:
        try:
            return _parse_json(_fetch(self.endpoint, timeout_s=self.timeout_s), self.peer)
        except PeerError as exc:
            raise PeerError(self.peer, exc.code, exc.message, request_id=exc.request_id) from exc


class RealContextPeer:
    """Loads an indic-context.v1 ModelResult (or error) from a configured endpoint."""

    def __init__(self, endpoint: str, *, timeout_s: float = 5.0) -> None:
        self.endpoint = endpoint
        self.timeout_s = timeout_s
        self.peer = "indic-context.v1"

    def propose(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        _ = request
        try:
            data = _parse_json(_fetch(self.endpoint, timeout_s=self.timeout_s), self.peer)
        except PeerError as exc:
            raise PeerError(self.peer, exc.code, exc.message, request_id=exc.request_id) from exc
        if data.get("code") in {"FORBIDDEN", "UNAUTHORIZED", "OUT_OF_SCOPE"}:
            raise PeerError(
                self.peer,
                "unauthorized_or_out_of_scope",
                str(data.get("message", "unauthorized")),
                request_id=str(data.get("request_id", "request-peer-1")),
            )
        if data.get("code") == "PEER_UNAVAILABLE":
            raise PeerError(self.peer, "unavailable", str(data.get("message", "unavailable")))
        outcome = data.get("outcome")
        if outcome not in {"PROPOSAL", "NEEDS_INPUT", "ESCALATE"}:
            raise PeerError(self.peer, "MALFORMED", "ModelResult.outcome missing or invalid")
        if "original_text" not in data or "language" not in data:
            raise PeerError(self.peer, "MALFORMED", "ModelResult provenance fields missing")
        return dict(data)
