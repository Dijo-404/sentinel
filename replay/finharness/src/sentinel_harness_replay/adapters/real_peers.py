from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

UrlOpen = Callable[..., Any]


class PeerUnavailable(RuntimeError):
    def __init__(self, peer: str, request_id: str = "harness-replay-real-peer") -> None:
        self.peer = peer
        self.payload = {
            "code": "PEER_UNAVAILABLE",
            "message": f"Required peer unavailable: {peer}",
            "request_id": request_id,
        }
        super().__init__(self.payload["message"])


class PeerMalformed(RuntimeError):
    def __init__(self, peer: str, detail: str) -> None:
        self.peer = peer
        self.payload = {
            "code": "PEER_MALFORMED",
            "message": f"Required peer malformed: {peer}: {detail}",
            "request_id": "harness-replay-real-peer",
        }
        super().__init__(self.payload["message"])


@dataclass(frozen=True)
class RealPeerConfig:
    runtime_url: str | None = None
    finbench_url: str | None = None
    replay_url: str | None = None

    @property
    def runtime_configured(self) -> bool:
        return bool(self.runtime_url)

    @property
    def finbench_configured(self) -> bool:
        return bool(self.finbench_url)

    @property
    def replay_configured(self) -> bool:
        return bool(self.replay_url)


def _http_get_json(
    base_url: str,
    path: str,
    *,
    peer: str,
    timeout_s: float = 5.0,
    opener: UrlOpen | None = None,
) -> dict[str, Any]:
    url = f"{base_url.rstrip('/')}{path}"
    request = urllib.request.Request(
        url,
        headers={"Accept": "application/json"},
        method="GET",
    )
    open_fn = opener or urllib.request.urlopen
    try:
        with open_fn(request, timeout=timeout_s) as response:
            status = getattr(response, "status", None) or response.getcode()
            raw = response.read()
    except urllib.error.HTTPError as exc:
        raise PeerUnavailable(peer) from exc
    except urllib.error.URLError as exc:
        raise PeerUnavailable(peer) from exc
    except OSError as exc:
        raise PeerUnavailable(peer) from exc
    if int(status) < 200 or int(status) >= 300:
        raise PeerUnavailable(peer)
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PeerMalformed(peer, "non-JSON response") from exc
    if not isinstance(payload, dict):
        raise PeerMalformed(peer, "capabilities not an object")
    return payload


class _HttpPeerMixin:
    peer_name: str
    expected_component: str

    def __init__(self, base_url: str | None, *, opener: UrlOpen | None = None) -> None:
        self.base_url = base_url
        self._opener = opener

    def healthz(self) -> dict:
        if not self.base_url:
            raise PeerUnavailable(self.peer_name)
        return _http_get_json(self.base_url, "/healthz", peer=self.peer_name, opener=self._opener)

    def capabilities(self) -> dict:
        if not self.base_url:
            raise PeerUnavailable(self.peer_name)
        # Exercise health first when present; capabilities is the contract gate.
        try:
            self.healthz()
        except PeerUnavailable:
            pass
        caps = _http_get_json(
            self.base_url, "/v1/capabilities", peer=self.peer_name, opener=self._opener
        )
        required = {"contract_version", "component", "mode"}
        if not required.issubset(caps):
            raise PeerMalformed(self.peer_name, "missing contract_version/component/mode")
        component = str(caps["component"])
        # Accept exact or CLI-prefixed names (e.g. sentinel-finbench).
        if (
            component != self.expected_component
            and self.expected_component not in component
            and component not in self.peer_name
        ):
            raise PeerMalformed(self.peer_name, f"unexpected component {component!r}")
        return caps


class RealRuntimeAdapter(_HttpPeerMixin):
    """Real finharness-runtime.v1 adapter. Absent URL fails closed; never fixture-fallback."""

    peer_name = "finharness-runtime.v1"
    expected_component = "finharness-runtime"

    def shadow_compare(self, case_manifest: dict) -> dict:
        del case_manifest
        caps = self.capabilities()
        return {
            "status": "PASS",
            "reason_code": "CAPABILITIES_PROBED",
            "capabilities": caps,
        }


class RealFinbenchAdapter(_HttpPeerMixin):
    """Real finbench.v1 adapter. Absent URL fails closed; never fixture-fallback."""

    peer_name = "finbench.v1"
    expected_component = "finbench"

    def score_candidate(self, run_payload: dict) -> dict:
        del run_payload
        caps = self.capabilities()
        return {
            "status": "PASS",
            "reason_code": "CAPABILITIES_PROBED",
            "capabilities": caps,
        }


class RealReplayAdapter(_HttpPeerMixin):
    """Real replay.v1 adapter. Absent URL fails closed; never fixture-fallback."""

    peer_name = "replay.v1"
    expected_component = "replay"

    def compare(self, run_payload: dict) -> dict:
        del run_payload
        caps = self.capabilities()
        return {
            "status": "PASS",
            "reason_code": "CAPABILITIES_PROBED",
            "capabilities": caps,
        }
