"""Opaque ID generation."""

from __future__ import annotations

import secrets


class SecureIdGenerator:
    def new_id(self, prefix: str) -> str:
        return f"{prefix}-{secrets.token_hex(8)}"
