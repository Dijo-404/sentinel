"""Original-byte provider webhook signature verification."""

from __future__ import annotations

import hmac
from hashlib import sha256


def signature_hex(raw_body: bytes, *, key: str) -> str:
    digest = hmac.new(key.encode("utf-8"), raw_body, sha256).hexdigest()
    return digest.lower()


def verify_signature(raw_body: bytes, *, key: str, provided: str) -> bool:
    if not provided:
        return False
    expected = signature_hex(raw_body, key=key)
    return hmac.compare_digest(expected, provided.strip().lower())
