"""Canonical digest helpers; retain original bytes rather than re-serializing parsed JSON."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def sha256_hex(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def canonical_json_bytes(value: Any) -> bytes:
    """Baseline serialization used only when constructing synthetic snapshot bytes."""
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
