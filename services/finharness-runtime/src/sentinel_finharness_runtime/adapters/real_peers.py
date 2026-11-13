"""Real-peer adapters. Fail closed when base URLs are absent. Never fixture-fallback."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

from sentinel_finharness_runtime.domain.errors import PeerError


@dataclass(frozen=True)
class RealPeerConfig:
    evidence_url: str | None = None
    policy_url: str | None = None
    ledger_url: str | None = None
    verifier_url: str | None = None
    indic_context_url: str | None = None
    sdk_url: str | None = None

    @property
    def any_configured(self) -> bool:
        return any(
            (
                self.evidence_url,
                self.policy_url,
                self.ledger_url,
                self.verifier_url,
                self.indic_context_url,
                self.sdk_url,
            )
        )


def _require_url(url: str | None, peer: str) -> str:
    if not url:
        raise PeerError(peer, "unavailable", "real peer base URL not configured")  # type: ignore[arg-type]
    return url


def _post_json(url: str, peer: str, path: str, body: Mapping[str, Any]) -> Mapping[str, Any]:
    import json

    target = url.rstrip("/") + path
    data = json.dumps(dict(body)).encode("utf-8")
    req = Request(target, data=data, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urlopen(req, timeout=2) as resp:  # noqa: S310 — operator-configured peer URL
            payload = json.loads(resp.read().decode("utf-8"))
    except URLError as exc:
        raise PeerError(peer, "unavailable", str(exc.reason)) from exc  # type: ignore[arg-type]
    except Exception as exc:  # noqa: BLE001
        raise PeerError(peer, "unavailable", str(exc)) from exc  # type: ignore[arg-type]
    if not isinstance(payload, dict):
        raise PeerError(peer, "malformed", "response was not an object")  # type: ignore[arg-type]
    return payload


class RealEvidenceAdapter:
    def __init__(self, base_url: str | None) -> None:
        self._base = base_url

    def collect(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        url = _require_url(self._base, "evidence.v1")
        return _post_json(url, "evidence.v1", "/v1/evidence/collect", request)


class RealPolicyAdapter:
    def __init__(self, base_url: str | None) -> None:
        self._base = base_url

    def evaluate(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        url = _require_url(self._base, "policy.v1")
        return _post_json(url, "policy.v1", "/v1/evaluate", request)


class RealLedgerAdapter:
    def __init__(self, base_url: str | None) -> None:
        self._base = base_url

    def create_proposal(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        url = _require_url(self._base, "action-ledger.v1")
        return _post_json(url, "action-ledger.v1", "/v1/actions/proposals", request)

    def reserve(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        url = _require_url(self._base, "action-ledger.v1")
        return _post_json(url, "action-ledger.v1", "/v1/actions/reservations", request)

    def get_action(self, action_id: str) -> Mapping[str, Any]:
        url = _require_url(self._base, "action-ledger.v1")
        return _post_json(url, "action-ledger.v1", f"/v1/actions/{action_id}/lookup", {})

    def query_by_provider_ref(self, provider_ref: str) -> Mapping[str, Any]:
        url = _require_url(self._base, "action-ledger.v1")
        return _post_json(
            url,
            "action-ledger.v1",
            "/v1/actions/by-provider-ref",
            {"provider_ref": provider_ref},
        )


class RealVerifierAdapter:
    def __init__(self, base_url: str | None) -> None:
        self._base = base_url

    def assess(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        url = _require_url(self._base, "verifier.v1")
        return _post_json(url, "verifier.v1", "/v1/assessments", request)


class RealIndicContextAdapter:
    def __init__(self, base_url: str | None) -> None:
        self._base = base_url

    def propose(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        url = _require_url(self._base, "indic-context.v1")
        return _post_json(url, "indic-context.v1", "/v1/proposals", request)


class RealSdkAdapter:
    def __init__(self, base_url: str | None) -> None:
        self._base = base_url

    def run_read_path(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        url = _require_url(self._base, "finharness-sdk.v1")
        return _post_json(url, "finharness-sdk.v1", "/v1/read-path", request)
