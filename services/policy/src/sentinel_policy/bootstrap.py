"""Composition root: config, tokens, clock, app."""

from __future__ import annotations

import os
from pathlib import Path

from sentinel_policy.adapters.auth import TokenMap
from sentinel_policy.adapters.clock import SystemClock
from sentinel_policy.adapters.http import create_app
from sentinel_policy.application.evaluate import EvaluatePolicy

MODULE_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PRINCIPALS = MODULE_ROOT / "contracts" / "principals.json"


def build_app(
    *,
    principals_path: Path | None = None,
    mode: str | None = None,
):
    path = principals_path or Path(
        os.environ.get("POLICY_PRINCIPALS_PATH", str(DEFAULT_PRINCIPALS))
    )
    if not path.is_absolute():
        path = (Path.cwd() / path).resolve()
    tokens = TokenMap.from_path(path)
    evaluate = EvaluatePolicy(SystemClock())
    return create_app(
        evaluate=evaluate,
        tokens=tokens,
        mode=mode or os.environ.get("POLICY_MODE", "fixture"),
    )
