from __future__ import annotations

import os

from sentinel_simulator.domain.webhooks import (
    DEFAULT_WEBHOOK_HMAC_KEY,
    canonical_webhook_bytes,
    sign_webhook,
    signed_webhook_envelope,
)

__all__ = [
    "DEFAULT_WEBHOOK_HMAC_KEY",
    "canonical_webhook_bytes",
    "resolve_webhook_hmac_key",
    "sign_webhook",
    "signed_webhook_envelope",
]


def resolve_webhook_hmac_key(explicit: str | None = None) -> str:
    if explicit is not None:
        return explicit
    return os.environ.get("SIMULATOR_WEBHOOK_HMAC_KEY", DEFAULT_WEBHOOK_HMAC_KEY)
