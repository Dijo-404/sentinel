"""Domain transition invariants."""

from __future__ import annotations

import pytest

from sentinel_merchant_inbox.contracts import ExceptionItem
from sentinel_merchant_inbox.domain import rules
from sentinel_merchant_inbox.domain.errors import ConflictError, ValidationError


def _item(**overrides) -> ExceptionItem:
    base = dict(
        item_id="exc-1",
        tenant_id="demo-tenant-a",
        merchant_ref="merchant-demo-1",
        kind="PAID_UNFULFILLED",
        amount_minor=1500,
        currency="INR",
        status="OPEN",
        notes=[],
    )
    base.update(overrides)
    return ExceptionItem(**base)


def test_assign_sets_assignee_and_assigned_status():
    updated = rules.apply_assign(_item(), assignee="staff-a")
    assert updated.status == "ASSIGNED"
    assert updated.assignee == "staff-a"
    assert updated.amount_minor == 1500


def test_note_appends_without_status_change():
    updated = rules.apply_note(_item(status="ASSIGNED", assignee="staff-a"), note="called merchant")
    assert updated.status == "ASSIGNED"
    assert updated.notes == ["called merchant"]


def test_escalate_never_closes_or_resolves():
    updated = rules.apply_escalate(_item(), reason_code="NEEDS_SUPERVISOR")
    assert updated.status == "ESCALATED"
    assert updated.status != "CLOSED"
    rules.assert_escalation_not_resolution(updated)


def test_escalate_rejects_closed_item():
    with pytest.raises(ConflictError):
        rules.apply_escalate(_item(status="CLOSED"), reason_code="x")


def test_assign_requires_nonempty_assignee():
    with pytest.raises(ValidationError):
        rules.apply_assign(_item(), assignee="  ")


def test_amount_minor_stays_integer():
    updated = rules.apply_escalate(_item(amount_minor=99900), reason_code="SLA")
    assert isinstance(updated.amount_minor, int)
    assert updated.amount_minor == 99900
