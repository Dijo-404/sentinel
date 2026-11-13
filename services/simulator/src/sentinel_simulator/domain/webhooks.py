from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any

DEFAULT_WEBHOOK_HMAC_KEY = "demo-simulator-hmac-key"


def canonical_webhook_bytes(payload: dict[str, Any]) -> bytes:
    """Stable JSON bytes for HMAC; keys sorted, no whitespace."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


def sign_webhook(raw_body: bytes, *, key: str) -> str:
    """Lowercase hex HMAC-SHA256 over original bytes (verifier.v1 compatible)."""
    return hmac.new(key.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()


def signed_webhook_envelope(
    payload: dict[str, Any],
    *,
    key: str,
) -> dict[str, Any]:
    raw = canonical_webhook_bytes(payload)
    signature = sign_webhook(raw, key=key)
    return {
        "body": payload,
        "raw_body": raw.decode("utf-8"),
        "signature": signature,
        "headers": {
            "Content-Type": "application/json",
            "X-Sentinel-Signature": signature,
        },
    }
