"""Narrow ports: staff persistence, case-api peer, identity memberships, clock."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from ..domain.types import (
    CaseSnapshot,
    IdentityMembership,
    MerchantStaff,
    Principal,
    StaffActivity,
)


class Clock(Protocol):
    def now(self) -> datetime: ...


class StaffStore(Protocol):
    def create(self, staff: MerchantStaff) -> MerchantStaff: ...

    def get(self, *, tenant_id: str, staff_id: str) -> MerchantStaff | None: ...

    def save(self, staff: MerchantStaff) -> MerchantStaff: ...

    def list_for_merchant(
        self, *, tenant_id: str, merchant_ref: str
    ) -> tuple[MerchantStaff, ...]: ...

    def append_activity(self, event: StaffActivity) -> StaffActivity: ...

    def list_activity(self, *, staff_id: str) -> tuple[StaffActivity, ...]: ...


class CaseApiPort(Protocol):
    """case-api.v1 read surface used when activity references a case."""

    def get_case(self, case_id: str, *, principal: Principal) -> CaseSnapshot: ...


class IdentityMembershipPort(Protocol):
    """identity.v1 merchant membership read surface (authoritative projection source)."""

    def list_memberships(
        self,
        *,
        tenant_id: str,
        merchant_ref: str,
        principal: Principal,
    ) -> tuple[IdentityMembership, ...]: ...
