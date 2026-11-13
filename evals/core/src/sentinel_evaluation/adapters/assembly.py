from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sentinel_evaluation.application.evaluate import EvaluateError

STUB_DIR = Path(__file__).resolve().parents[3] / "tests" / "stubs" / "core_assembly"


class StubAssemblyPeer:
    """Local core-assembly.v1 doubles. Never silently upgrades failure to success."""

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


class RejectingRealAssemblyPeer:
    """Real-peer adapter placeholder: refuses fixture fallback when peer missing."""

    def __init__(self, base_url: str | None = None) -> None:
        self._base_url = base_url

    def probe(self) -> dict[str, Any]:
        if not self._base_url:
            raise EvaluateError(
                "PEER_UNAVAILABLE",
                "core-assembly.v1 real peer URL not configured; fixture fallback disabled",
            )
        raise EvaluateError(
            "PEER_UNAVAILABLE",
            f"core-assembly.v1 real peer at {self._base_url} not contacted in this module; "
            "assemble separately",
        )
