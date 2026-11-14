"""In-process identity.v1 membership stub for fixture mode."""

from __future__ import annotations

from typing import Any

from ..application.errors import (
    PeerMalformedError,
    PeerUnauthorizedError,
    PeerUnavailableError,
)
from ..domain.types import IdentityMembership, Principal


class StubIdentityMemberships:
    """Fixture peer. Modes mirror tests/stubs/identity cases."""

    def __init__(self, *, mode: str = "valid") -> None:
        if mode not in {
            "valid",
            "unavailable",
            "malformed",
            "unauthorized_or_out_of_scope",
        }:
            raise ValueError(f"unsupported stub mode: {mode}")
        self.mode = mode
        self.memberships: dict[tuple[str, str], list[dict[str, Any]]] = {
            ("tenant-demo", "merchant-demo-1"): [
                {
                    "membership_id": "mm-demo-1",
                    "assignment_id": "asg-merchant-1",
                    "user_id": "user-merchant-1",
                    "tenant_id": "tenant-demo",
                    "merchant_ref": "merchant-demo-1",
                    "display_name": "Demo Merchant Approver",
                    "subroles": ["approver"],
                    "status": "active",
                },
                {
                    "membership_id": "mm-demo-2",
                    "assignment_id": "asg-merchant-2",
                    "user_id": "user-merchant-2",
                    "tenant_id": "tenant-demo",
                    "merchant_ref": "merchant-demo-1",
                    "display_name": "Demo Merchant Admin",
                    "subroles": ["admin"],
                    "status": "active",
                },
            ]
        }

    def seed(
        self,
        *,
        tenant_id: str,
        merchant_ref: str,
        rows: list[dict[str, Any]],
    ) -> None:
        self.memberships[(tenant_id, merchant_ref)] = list(rows)

    def list_memberships(
        self,
        *,
        tenant_id: str,
        merchant_ref: str,
        principal: Principal,
    ) -> tuple[IdentityMembership, ...]:
        del principal
        if self.mode == "unavailable":
            raise PeerUnavailableError("Required peer unavailable")
        if self.mode == "malformed":
            raise PeerMalformedError("Malformed identity membership response")
        if self.mode == "unauthorized_or_out_of_scope":
            raise PeerUnauthorizedError("Unauthorized or out of scope")
        rows = self.memberships.get((tenant_id, merchant_ref), [])
        return tuple(IdentityMembership.from_wire(row) for row in rows)
