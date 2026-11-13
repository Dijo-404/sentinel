"""Strip secrets from log-bound strings. Never emit API keys or bearer tokens."""

from __future__ import annotations

import re

_SECRET_PATTERNS = (
    re.compile(r"(?i)authorization\s*:\s*bearer\s+\S+"),
    re.compile(r"(?i)\bbearer\s+[a-z0-9._\-]+"),
    re.compile(r"(?i)(api[_-]?key|sarvam[_-]?api[_-]?key)\s*[=:]\s*\S+"),
    re.compile(r"(?i)\bsk-[a-z0-9\-_]{8,}"),
)

_LEAK_HINTS = (
    re.compile(r"(?i)api[_-]?key\s*[=:]\s*(?!\[REDACTED\])\S+"),
    re.compile(r"(?i)\bbearer\s+(?!\[REDACTED\])[a-z0-9._\-]+"),
    re.compile(r"(?i)\bsk-[a-z0-9\-_]{8,}"),
)


def redact_secrets(message: str) -> str:
    redacted = message
    for pattern in _SECRET_PATTERNS:
        redacted = pattern.sub("[REDACTED]", redacted)
    return redacted


def contains_secret(message: str) -> bool:
    return any(pattern.search(message) for pattern in _LEAK_HINTS)
