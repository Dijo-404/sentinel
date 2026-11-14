"""Opaque bearer token → Principal mapping (local synthetic credentials)."""

from __future__ import annotations

import json
from pathlib import Path

from sentinel_merchant_sla.contracts import Principal, SlaInputError, parse_principal


class TokenMap:
    def __init__(self, mapping: dict[str, Principal]) -> None:
        self._mapping = mapping

    @property
    def tokens(self):
        return self._mapping

    @classmethod
    def from_path(cls, path: Path) -> TokenMap:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise SlaInputError("INVALID_CONFIG", "principals file must be an object")
        mapping: dict[str, Principal] = {}
        for token, principal_raw in raw.items():
            if not isinstance(token, str) or not token:
                raise SlaInputError("INVALID_CONFIG", "token keys must be nonempty strings")
            if not isinstance(principal_raw, dict):
                raise SlaInputError("INVALID_CONFIG", "principal values must be objects")
            mapping[token] = parse_principal(principal_raw)
        return cls(mapping)

    def resolve(self, authorization: str | None) -> Principal | None:
        if authorization is None:
            return None
        parts = authorization.split(" ", 1)
        if len(parts) != 2 or parts[0] != "Bearer" or not parts[1]:
            return None
        return self._mapping.get(parts[1])
