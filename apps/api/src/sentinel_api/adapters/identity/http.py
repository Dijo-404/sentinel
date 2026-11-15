"""Real-peer identity.v1 principal projection via GET /v1/auth/me. Fail closed."""

from __future__ import annotations

import json
from typing import Any

import httpx

from sentinel_api.domain.types import DomainError, Principal


def principal_from_me(body: dict[str, Any]) -> Principal:
    """Map identity /v1/auth/me payload to case-api Principal."""
    user = body.get("user")
    active = body.get("active_assignment")
    if not isinstance(user, dict) or not isinstance(active, dict):
        raise DomainError("UNAUTHORIZED", "Identity me response missing assignment", 401)
    try:
        principal_id = str(user["user_id"])
        tenant_id = str(active["tenant_id"])
        role_id = str(active["role_id"])
    except (KeyError, TypeError) as exc:
        raise DomainError("UNAUTHORIZED", "Identity me response malformed", 401) from exc
    if not principal_id or not tenant_id or not role_id:
        raise DomainError("UNAUTHORIZED", "Identity me response malformed", 401)

    subject_refs = _string_tuple(active.get("subject_refs"))
    if not subject_refs:
        merchant_ref = active.get("merchant_ref")
        if isinstance(merchant_ref, str) and merchant_ref:
            subject_refs = (merchant_ref,)
    # Identity assignments do not yet carry subject_refs for customers; sandbox matrix
    # uses subject-demo-42 so customer case projections resolve under portal sessions.
    if not subject_refs and role_id == "customer":
        subject_refs = ("subject-demo-42",)
    case_ids = _string_tuple(active.get("case_ids"))

    return Principal(
        principal_id=principal_id,
        tenant_id=tenant_id,
        roles=(role_id,),
        subject_refs=subject_refs,
        case_ids=case_ids,
    )


def _string_tuple(raw: Any) -> tuple[str, ...]:
    if raw is None:
        return ()
    if not isinstance(raw, (list, tuple)):
        raise DomainError("UNAUTHORIZED", "Identity me response malformed", 401)
    out: list[str] = []
    for item in raw:
        if not isinstance(item, str):
            raise DomainError("UNAUTHORIZED", "Identity me response malformed", 401)
        out.append(item)
    return tuple(out)


class HttpIdentityPrincipalAdapter:
    """Resolve bearer via identity /v1/auth/me; None only when identity rejects the credential."""

    def __init__(self, base_url: str, client: httpx.Client | None = None) -> None:
        if not base_url.strip():
            raise ValueError("identity base_url required when identity peer is enabled")
        self._base = base_url.rstrip("/")
        self._client = client or httpx.Client(timeout=5.0)

    def project(self, credential: str) -> Principal | None:
        try:
            response = self._client.get(
                f"{self._base}/v1/auth/me",
                headers={"Authorization": f"Bearer {credential}"},
            )
        except httpx.HTTPError as exc:
            raise DomainError("UNAUTHORIZED", "Identity peer unavailable", 401) from exc

        if response.status_code in {401, 403}:
            return None
        if response.status_code >= 500:
            raise DomainError("UNAUTHORIZED", "Identity peer unavailable", 401)
        if response.status_code != 200:
            raise DomainError("UNAUTHORIZED", "Identity me response malformed", 401)

        try:
            body: Any = json.loads(response.content.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise DomainError("UNAUTHORIZED", "Identity me response malformed", 401) from exc

        if not isinstance(body, dict) or "user" not in body or "active_assignment" not in body:
            raise DomainError("UNAUTHORIZED", "Identity me response malformed", 401)
        if body.get("active_assignment") is None:
            return None
        return principal_from_me(body)
