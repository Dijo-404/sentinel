"""Canonical action digest matching the contract baseline."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def canonical_action_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def action_digest(payload: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_action_bytes(payload)).hexdigest()
