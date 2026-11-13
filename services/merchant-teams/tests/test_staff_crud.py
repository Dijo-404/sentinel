"""Staff create/update/deactivate persistence."""

from __future__ import annotations

from tests.conftest import OPERATOR


def test_create_update_deactivate_persist(service):
    created = service.create(
        OPERATOR,
        merchant_ref="merchant-demo-1",
        display_name="Ada Merchant",
        roles=["operator", "approver"],
        approval_limit_minor=50000,
        currency="INR",
        staff_id="staff-demo-1",
    )
    assert created.active is True
    assert created.roles == ("operator", "approver")
    assert created.approval_limit_minor == 50000

    updated = service.update(
        OPERATOR,
        "staff-demo-1",
        display_name="Ada Ops",
        roles=["admin"],
        approval_limit_minor=10000,
        currency="INR",
    )
    assert updated.display_name == "Ada Ops"
    assert updated.roles == ("admin",)
    assert updated.approval_limit_minor == 10000

    deactivated = service.deactivate(OPERATOR, "staff-demo-1")
    assert deactivated.active is False
    again = service.get(OPERATOR, "staff-demo-1")
    assert again.active is False


def test_list_scoped_to_merchant(service):
    service.create(
        OPERATOR,
        merchant_ref="merchant-demo-1",
        display_name="One",
        roles=["viewer"],
        staff_id="staff-a",
    )
    rows = service.list_staff(OPERATOR, "merchant-demo-1")
    assert [row.staff_id for row in rows] == ["staff-a"]
