"""In-process staff store for fixture/unit tests."""

from __future__ import annotations

from ..domain.types import MerchantStaff, StaffActivity


class MemoryStaffStore:
    def __init__(self) -> None:
        self._staff: dict[tuple[str, str], MerchantStaff] = {}
        self._activity: dict[str, list[StaffActivity]] = {}

    def create(self, staff: MerchantStaff) -> MerchantStaff:
        key = (staff.tenant_id, staff.staff_id)
        if key in self._staff:
            raise ValueError("staff_id already exists")
        self._staff[key] = staff
        self._activity.setdefault(staff.staff_id, [])
        return staff

    def get(self, *, tenant_id: str, staff_id: str) -> MerchantStaff | None:
        return self._staff.get((tenant_id, staff_id))

    def save(self, staff: MerchantStaff) -> MerchantStaff:
        self._staff[(staff.tenant_id, staff.staff_id)] = staff
        return staff

    def list_for_merchant(self, *, tenant_id: str, merchant_ref: str) -> tuple[MerchantStaff, ...]:
        rows = [
            staff
            for (tid, _), staff in self._staff.items()
            if tid == tenant_id and staff.merchant_ref == merchant_ref
        ]
        return tuple(sorted(rows, key=lambda s: s.staff_id))

    def append_activity(self, event: StaffActivity) -> StaffActivity:
        # Append-only: never rewrite prior events.
        bucket = self._activity.setdefault(event.staff_id, [])
        bucket.append(event)
        return event

    def list_activity(self, *, staff_id: str) -> tuple[StaffActivity, ...]:
        return tuple(self._activity.get(staff_id, []))
