from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Callable
from pathlib import Path
from typing import Any

from sentinel_evaluation.application.evaluate import EvaluateError

STUB_DIR = Path(__file__).resolve().parents[3] / "tests" / "stubs" / "core_assembly"

UrlOpen = Callable[..., Any]


class StubAssemblyPeer:
    """Local core-assembly.v1 doubles / reference peers. Never silently upgrades failure."""

    def __init__(self, case: str = "valid", stub_dir: Path | None = None) -> None:
        self._case = case
        self._stub_dir = stub_dir or STUB_DIR

    def probe(self) -> dict[str, Any]:
        path = self._stub_dir / f"{self._case}.json"
        if not path.is_file():
            raise EvaluateError("PEER_UNAVAILABLE", f"Missing assembly stub: {path}")
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise EvaluateError("PEER_MALFORMED", f"Unreadable assembly stub: {exc}") from exc
        if self._case == "malformed":
            # Stub may be intentionally incomplete; still report MALFORMED.
            return {
                "status": "MALFORMED",
                "message": raw.get("message", "malformed assembly payload"),
                "payload": raw,
            }
        status = raw.get("status")
        if status is None:
            raise EvaluateError("PEER_MALFORMED", "Assembly stub missing status")
        return raw


class HttpAssemblyPeer:
    """
    Real-peer HTTP probe against a core-assembly.v1 base URL.

    Contacts `/healthz` (soft) and `/v1/capabilities`. No fixture fallback.
    """

    def __init__(
        self,
        base_url: str | None = None,
        *,
        timeout_s: float = 5.0,
        opener: UrlOpen | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/") if base_url else None
        self._timeout_s = timeout_s
        self._opener = opener or urllib.request.urlopen

    def probe(self) -> dict[str, Any]:
        if not self._base_url:
            raise EvaluateError(
                "PEER_UNAVAILABLE",
                "core-assembly.v1 real peer URL not configured; fixture fallback disabled",
            )
        self._get_optional_health()
        caps_raw = self._get_json("/v1/capabilities")
        return self._normalize_probe(caps_raw)

    def _get_optional_health(self) -> None:
        try:
            self._get_json("/healthz")
        except EvaluateError:
            # healthz optional; capabilities is authoritative
            return

    def _get_json(self, path: str) -> dict[str, Any]:
        assert self._base_url is not None
        url = f"{self._base_url}{path}"
        request = urllib.request.Request(
            url,
            headers={"Accept": "application/json"},
            method="GET",
        )
        try:
            with self._opener(request, timeout=self._timeout_s) as response:
                status = getattr(response, "status", None) or response.getcode()
                raw = response.read()
        except urllib.error.HTTPError as exc:
            if exc.code in (401, 403):
                raise EvaluateError(
                    "PEER_UNAUTHORIZED",
                    f"core-assembly.v1 {path} returned HTTP {exc.code}",
                ) from exc
            raise EvaluateError(
                "PEER_UNAVAILABLE",
                f"core-assembly.v1 {path} returned HTTP {exc.code}",
            ) from exc
        except urllib.error.URLError as exc:
            raise EvaluateError(
                "PEER_UNAVAILABLE",
                f"core-assembly.v1 peer unreachable: {exc.reason}",
            ) from exc
        except OSError as exc:
            raise EvaluateError(
                "PEER_UNAVAILABLE",
                f"core-assembly.v1 peer contact failed: {exc}",
            ) from exc
        if int(status) < 200 or int(status) >= 300:
            raise EvaluateError(
                "PEER_UNAVAILABLE",
                f"core-assembly.v1 {path} returned HTTP {status}",
            )
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise EvaluateError(
                "PEER_MALFORMED",
                f"core-assembly.v1 {path} returned non-JSON: {exc}",
            ) from exc
        if not isinstance(payload, dict):
            raise EvaluateError("PEER_MALFORMED", f"core-assembly.v1 {path} payload not an object")
        return payload

    def _normalize_probe(self, caps_raw: dict[str, Any]) -> dict[str, Any]:
        # Full probe envelope from local doubles / gated assembly services.
        if "status" in caps_raw and "capabilities" in caps_raw:
            return caps_raw
        # Raw /v1/capabilities from sentinel-core-assembly CLI/HTTP surface.
        required = {"contract_version", "component", "mode"}
        if not required.issubset(caps_raw):
            raise EvaluateError(
                "PEER_MALFORMED",
                "core-assembly.v1 capabilities missing contract_version/component/mode",
            )
        component = str(caps_raw["component"])
        if component in {"sentinel-core-assembly", "core-assembly.v1"}:
            component = "core-assembly"
        return {
            "status": "OK",
            "message": "HTTP core-assembly.v1 capabilities probe succeeded",
            "capabilities": {
                "contract_version": str(caps_raw["contract_version"]),
                "component": component,
                "mode": str(caps_raw["mode"]),
            },
            "evidence_mode": "real-component",
        }


# Back-compat alias: previous reject-only placeholder now contacts the peer when URL set.
RejectingRealAssemblyPeer = HttpAssemblyPeer
