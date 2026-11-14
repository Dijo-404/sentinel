"""Opaque bearer token → MerchantBinding (local synthetic credentials)."""

from __future__ import annotations

import json
from pathlib import Path

from sentinel_merchant_inbox.contracts import InboxInputError, MerchantBinding, parse_principal


class TokenMap:
    def __init__(self, mapping: dict[str, MerchantBinding]) -> None:
        self._mapping = mapping

    @property
    def tokens(self):
        return self._mapping

    @classmethod
    def from_path(cls, path: Path) -> TokenMap:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise InboxInputError("INVALID_CONFIG", "principals file must be an object")
        mapping: dict[str, MerchantBinding] = {}
        for token, entry in raw.items():
            if not isinstance(token, str) or not token:
                raise InboxInputError("INVALID_CONFIG", "token keys must be nonempty strings")
            if not isinstance(entry, dict):
                raise InboxInputError("INVALID_CONFIG", "token values must be objects")
            principal_raw = entry.get("principal")
            merchant_refs_raw = entry.get("merchant_refs")
            if not isinstance(principal_raw, dict):
                raise InboxInputError("INVALID_CONFIG", "principal must be an object")
            if not isinstance(merchant_refs_raw, list) or not all(
                isinstance(m, str) for m in merchant_refs_raw
            ):
                raise InboxInputError("INVALID_CONFIG", "merchant_refs must be a string array")
            mapping[token] = MerchantBinding(
                principal=parse_principal(principal_raw),
                merchant_refs=tuple(merchant_refs_raw),
            )
        return cls(mapping)

    def resolve(self, authorization: str | None) -> MerchantBinding | None:
        if authorization is None:
            return None
        parts = authorization.split(" ", 1)
        if len(parts) != 2 or parts[0] != "Bearer" or not parts[1]:
            return None
        return self._mapping.get(parts[1])
