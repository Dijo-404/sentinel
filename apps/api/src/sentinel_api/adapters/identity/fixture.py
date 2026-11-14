"""Fixture double: session/BFF credential → Principal. No live identity calls."""

from __future__ import annotations

import json
from pathlib import Path

from sentinel_api.domain.types import Principal


def principal_from_session_projection(raw: dict) -> Principal:
    """Map session-derived principal shape to existing Principal."""
    return Principal(
        principal_id=str(raw["principal_id"]),
        tenant_id=str(raw["tenant_id"]),
        roles=tuple(raw.get("roles") or ()),
        subject_refs=tuple(raw.get("subject_refs") or ()),
        case_ids=tuple(raw.get("case_ids") or ()),
    )


class FixtureIdentityPrincipalAdapter:
    """In-process identity projection catalog for fixture/demo mode."""

    def __init__(self, sessions: dict[str, Principal]) -> None:
        self._sessions = sessions

    @classmethod
    def from_path(cls, path: Path) -> FixtureIdentityPrincipalAdapter:
        data = json.loads(path.read_text(encoding="utf-8"))
        sessions = {
            credential: principal_from_session_projection(raw) for credential, raw in data.items()
        }
        return cls(sessions)

    @classmethod
    def from_mapping(cls, data: dict[str, dict]) -> FixtureIdentityPrincipalAdapter:
        sessions = {
            credential: principal_from_session_projection(raw) for credential, raw in data.items()
        }
        return cls(sessions)

    def project(self, credential: str) -> Principal | None:
        return self._sessions.get(credential)

    def session_credentials(self) -> tuple[str, ...]:
        return tuple(self._sessions.keys())
