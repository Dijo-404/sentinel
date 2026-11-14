"""Bearer resolution: identity session projection first, then opaque token map."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Protocol

from sentinel_api.domain.types import DomainError, Principal


class IdentityPrincipalPort(Protocol):
    def project(self, credential: str) -> Principal | None:
        """Return Principal for a session/BFF credential, or None if unknown here."""
        ...


class TokenMap:
    def __init__(self, tokens: dict[str, Principal]) -> None:
        self._tokens = tokens

    @property
    def tokens(self) -> dict[str, Principal]:
        return self._tokens

    @classmethod
    def from_path(cls, path: Path) -> TokenMap:
        data = json.loads(path.read_text(encoding="utf-8"))
        tokens: dict[str, Principal] = {}
        for token, raw in data.items():
            tokens[token] = Principal(
                principal_id=raw["principal_id"],
                tenant_id=raw["tenant_id"],
                roles=tuple(raw["roles"]),
                subject_refs=tuple(raw.get("subject_refs", [])),
                case_ids=tuple(raw.get("case_ids", [])),
            )
        return cls(tokens)

    @classmethod
    def from_mapping(cls, data: dict[str, dict]) -> TokenMap:
        tokens = {
            token: Principal(
                principal_id=raw["principal_id"],
                tenant_id=raw["tenant_id"],
                roles=tuple(raw["roles"]),
                subject_refs=tuple(raw.get("subject_refs", [])),
                case_ids=tuple(raw.get("case_ids", [])),
            )
            for token, raw in data.items()
        }
        return cls(tokens)

    def resolve(self, authorization: str | None) -> Principal:
        if not authorization or not authorization.startswith("Bearer "):
            raise DomainError("UNAUTHORIZED", "Bearer token required", 401)
        token = authorization.removeprefix("Bearer ").strip()
        principal = self._tokens.get(token)
        if principal is None:
            raise DomainError("UNAUTHORIZED", "Unknown bearer token", 401)
        return principal


class CompositePrincipalResolver:
    """Identity-validated / BFF-minted projection, then opaque service/human token map."""

    def __init__(
        self,
        *,
        identity: IdentityPrincipalPort | None,
        tokens: TokenMap,
    ) -> None:
        self._identity = identity
        self._tokens = tokens

    @property
    def tokens(self) -> dict[str, Principal]:
        return self._tokens.tokens

    def resolve(self, authorization: str | None) -> Principal:
        if not authorization or not authorization.startswith("Bearer "):
            raise DomainError("UNAUTHORIZED", "Bearer token required", 401)
        credential = authorization.removeprefix("Bearer ").strip()
        if self._identity is not None:
            projected = self._identity.project(credential)
            if projected is not None:
                return projected
        principal = self._tokens.tokens.get(credential)
        if principal is None:
            raise DomainError("UNAUTHORIZED", "Unknown bearer token", 401)
        return principal
