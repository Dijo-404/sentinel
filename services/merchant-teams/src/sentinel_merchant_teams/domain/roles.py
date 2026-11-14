"""Staff role validation — merchant subroles only; no platform authority."""

from __future__ import annotations

from .types import PLATFORM_AUTHORITY_ROLES, STAFF_ROLES


def _is_platform_authority(role: str) -> bool:
    value = role.strip()
    if value in PLATFORM_AUTHORITY_ROLES:
        return True
    if value.startswith("platform_"):
        return True
    if ":" in value:
        namespace, _, rest = value.partition(":")
        if namespace in {"platform", "identity"} or rest in PLATFORM_AUTHORITY_ROLES:
            return True
    return False


def normalize_roles(roles: list[str] | tuple[str, ...]) -> tuple[str, ...]:
    if not roles:
        raise ValueError("roles must be a nonempty list")
    normalized: list[str] = []
    seen: set[str] = set()
    for role in roles:
        if not isinstance(role, str) or not role.strip():
            raise ValueError("roles entries must be nonempty strings")
        value = role.strip()
        if _is_platform_authority(value):
            raise ValueError(
                "platform role grants are owned by identity; "
                "merchant-teams cannot assign competing platform roles"
            )
        if value not in STAFF_ROLES:
            raise ValueError(f"unsupported staff role: {value}")
        if value not in seen:
            seen.add(value)
            normalized.append(value)
    return tuple(normalized)
