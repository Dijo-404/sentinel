"""Bearer token → synthetic merchant principal map."""

from __future__ import annotations

from dataclasses import dataclass

from sentinel_merchant_refunds.domain.errors import UnauthorizedError
from sentinel_merchant_refunds.domain.types import Principal


@dataclass(frozen=True)
class TokenPrincipalMap:
    tokens: dict[str, Principal]

    def resolve(self, authorization: str | None) -> Principal:
        if not authorization or not authorization.startswith("Bearer "):
            raise UnauthorizedError("Valid bearer token required")
        token = authorization.removeprefix("Bearer ").strip()
        principal = self.tokens.get(token)
        if principal is None:
            raise UnauthorizedError("Valid bearer token required")
        return principal


def demo_principals(
    *,
    tenant_id: str = "tenant-demo-1",
    merchant_ref: str = "merchant-demo-1",
) -> dict[str, Principal]:
    staff = Principal(
        principal_id="staff-demo-1",
        tenant_id=tenant_id,
        merchant_ref=merchant_ref,
        roles=["merchant_staff"],
    )
    supervisor = Principal(
        principal_id="supervisor-demo-1",
        tenant_id=tenant_id,
        merchant_ref=merchant_ref,
        roles=["merchant_supervisor", "merchant_staff"],
    )
    return {
        "token-merchant-refunds-demo": staff,
        "token-merchant-supervisor-demo": supervisor,
    }
