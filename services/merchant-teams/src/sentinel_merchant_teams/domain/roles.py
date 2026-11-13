"""Staff role validation."""

from __future__ import annotations

from .types import STAFF_ROLES


def normalize_roles(roles: list[str] | tuple[str, ...]) -> tuple[str, ...]:
    if not roles:
        raise ValueError("roles must be a nonempty list")
    normalized: list[str] = []
    seen: set[str] = set()
    for role in roles:
        if not isinstance(role, str) or not role.strip():
            raise ValueError("roles entries must be nonempty strings")
        value = role.strip()
        if value not in STAFF_ROLES:
            raise ValueError(f"unsupported staff role: {value}")
        if value not in seen:
            seen.add(value)
            normalized.append(value)
    return tuple(normalized)
