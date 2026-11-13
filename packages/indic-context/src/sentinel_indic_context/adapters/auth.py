"""Synthetic bearer token map. Never trust model-supplied principals."""

from __future__ import annotations

from typing import Any

from sentinel_indic_context.application.errors import UnauthorizedError
from sentinel_indic_context.domain.types import Principal


class TokenMapAuth:
    def __init__(self, token_map: dict[str, Any]) -> None:
        self._map = token_map

    def authenticate(self, authorization: str | None) -> Principal:
        if not authorization or not authorization.startswith("Bearer "):
            raise UnauthorizedError("Missing bearer token")
        token = authorization.removeprefix("Bearer ").strip()
        raw = self._map.get(token)
        if raw is None:
            raise UnauthorizedError("Unknown bearer token")
        return Principal.model_validate(raw)
