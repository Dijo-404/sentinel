"""Real-peer adapter: load peer RunReport JSON from configured paths/URLs.

Never silently falls back to fixture success when a peer is missing or bad.
"""

from __future__ import annotations

import json
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from sentinel_release_mvp.contracts import (
    CONTRACT_VERSION,
    PeerError,
    RunInput,
    RunReport,
)


class RealPeerRunner:
    """Reads a peer RunReport from a file path or http(s) URL.

    Configuration maps port -> endpoint. Fixture substitution is forbidden.
    """

    def __init__(self, port: str, endpoint: str, *, timeout_s: float = 5.0) -> None:
        self.port = port
        self.endpoint = endpoint
        self.timeout_s = timeout_s

    def run(self, request: RunInput) -> RunReport:
        if not self.endpoint:
            raise PeerError("PEER_UNAVAILABLE", f"{self.port} endpoint not configured")
        try:
            raw = self._fetch()
        except PeerError:
            raise
        except (OSError, URLError, HTTPError, TimeoutError) as exc:
            raise PeerError("PEER_UNAVAILABLE", f"{self.port} unavailable: {exc}") from exc
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise PeerError("MALFORMED", f"{self.port} malformed JSON: {exc}") from exc
        if not isinstance(data, dict):
            raise PeerError("MALFORMED", f"{self.port} response must be an object")
        if data.get("code") in {"FORBIDDEN", "UNAUTHORIZED", "OUT_OF_SCOPE"}:
            raise PeerError(
                str(data["code"]),
                str(data.get("message", "unauthorized or out of scope")),
                request_id=str(data.get("request_id", "request-peer-1")),
            )
        try:
            report = RunReport.from_dict(data)
        except Exception as exc:  # ContractError or TypeError
            raise PeerError("MALFORMED", f"{self.port} incompatible payload: {exc}") from exc
        if report.contract_version != CONTRACT_VERSION:
            raise PeerError("INCOMPATIBLE_CONTRACT", "peer contract_version mismatch")
        # Echo run_id binding for traceability; peer may use its own.
        _ = request
        return report

    def _fetch(self) -> str:
        if self.endpoint.startswith("file:") or "://" not in self.endpoint:
            path = Path(self.endpoint.removeprefix("file://"))
            if not path.is_file():
                raise PeerError("PEER_UNAVAILABLE", f"{self.port} file missing: {path}")
            return path.read_text(encoding="utf-8")
        req = Request(self.endpoint, headers={"Accept": "application/json"})
        with urlopen(req, timeout=self.timeout_s) as resp:  # noqa: S310 — operator-configured
            if getattr(resp, "status", 200) in {401, 403}:
                raise PeerError("FORBIDDEN", f"{self.port} unauthorized")
            return resp.read().decode("utf-8")


def runners_from_config(config: dict[str, str]) -> dict[str, RealPeerRunner]:
    return {port: RealPeerRunner(port, endpoint) for port, endpoint in config.items()}
