from __future__ import annotations

import json
from pathlib import Path

CASES = ("valid", "unavailable", "malformed", "unauthorized_or_out_of_scope")
_DIR = Path(__file__).resolve().parent


def load_case(name: str) -> dict:
    if name not in CASES:
        raise KeyError(name)
    return json.loads((_DIR / f"{name}.json").read_text(encoding="utf-8"))


class FinbenchStub:
    """In-process finbench.v1 double. Case selects response behavior."""

    def __init__(self, case: str = "valid") -> None:
        self.case = case
        self._payload = load_case(case)

    def capabilities(self) -> dict:
        if self.case == "unavailable":
            raise RuntimeError(self._payload["error"]["message"])
        if self.case == "malformed":
            return self._payload["capabilities"]
        if self.case == "unauthorized_or_out_of_scope":
            raise PermissionError(self._payload["error"]["message"])
        return self._payload["capabilities"]

    def score_candidate(self, run_payload: dict) -> dict:
        del run_payload
        if self.case == "unavailable":
            raise RuntimeError(self._payload["error"]["message"])
        if self.case == "unauthorized_or_out_of_scope":
            raise PermissionError(self._payload["error"]["message"])
        if self.case == "malformed":
            return self._payload["score_response"]
        return self._payload["score_response"]
