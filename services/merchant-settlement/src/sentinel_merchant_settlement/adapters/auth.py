"""Opaque bearer token → Principal mapping (local synthetic credentials)."""

from __future__ import annotations

import json
from pathlib import Path

from sentinel_merchant_settlement.application.errors import UnauthorizedError, ValidationError
from sentinel_merchant_settlement.domain.types import Principal


def parse_principal(raw: dict) -> Principal:
    required = {"principal_id", "tenant_id", "roles", "subject_refs", "case_ids"}
    if set(raw) != required:
        raise ValidationError("principal must have exact baseline fields")
    if not isinstance(raw["roles"], list) or not isinstance(raw["subject_refs"], list):
        raise ValidationError("roles and subject_refs must be arrays")
    if not isinstance(raw["case_ids"], list):
        raise ValidationError("case_ids must be an array")
    return Principal(
        principal_id=str(raw["principal_id"]),
        tenant_id=str(raw["tenant_id"]),
        roles=tuple(str(r) for r in raw["roles"]),
        subject_refs=tuple(str(s) for s in raw["subject_refs"]),
        case_ids=tuple(str(c) for c in raw["case_ids"]),
    )


class TokenMap:
    def __init__(self, mapping: dict[str, Principal]) -> None:
        self._mapping = mapping

    @classmethod
    def from_path(cls, path: Path) -> TokenMap:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValidationError("principals file must be an object")
        mapping: dict[str, Principal] = {}
        for token, principal_raw in raw.items():
            if not isinstance(token, str) or not token:
                raise ValidationError("token keys must be nonempty strings")
            if not isinstance(principal_raw, dict):
                raise ValidationError("principal values must be objects")
            mapping[token] = parse_principal(principal_raw)
        return cls(mapping)

    def resolve(self, authorization: str | None) -> Principal:
        if authorization is None:
            raise UnauthorizedError("Valid bearer token required")
        parts = authorization.split(" ", 1)
        if len(parts) != 2 or parts[0] != "Bearer" or not parts[1]:
            raise UnauthorizedError("Valid bearer token required")
        principal = self._mapping.get(parts[1])
        if principal is None:
            raise UnauthorizedError("Valid bearer token required")
        return principal
