"""Inbox transitions. Escalation is never verified financial resolution."""

from __future__ import annotations

from sentinel_merchant_inbox.contracts import ExceptionItem, ExceptionKind, ExceptionStatus
from sentinel_merchant_inbox.domain.errors import ConflictError, ValidationError

ASSIGNABLE: frozenset[ExceptionStatus] = frozenset({"OPEN", "ASSIGNED"})
NOTEABLE: frozenset[ExceptionStatus] = frozenset({"OPEN", "ASSIGNED", "ESCALATED"})
ESCALATABLE: frozenset[ExceptionStatus] = frozenset({"OPEN", "ASSIGNED", "ESCALATED"})


def apply_assign(item: ExceptionItem, *, assignee: str) -> ExceptionItem:
    if not assignee or not assignee.strip():
        raise ValidationError("assignee must be a nonempty string")
    if item.status not in ASSIGNABLE:
        raise ConflictError(f"Cannot assign item in status {item.status}")
    return ExceptionItem(
        item_id=item.item_id,
        tenant_id=item.tenant_id,
        merchant_ref=item.merchant_ref,
        kind=item.kind,
        amount_minor=item.amount_minor,
        currency=item.currency,
        status="ASSIGNED",
        notes=list(item.notes),
        case_id=item.case_id,
        transaction_ref=item.transaction_ref,
        assignee=assignee.strip(),
    )


def apply_note(item: ExceptionItem, *, note: str) -> ExceptionItem:
    if not note or not note.strip():
        raise ValidationError("note must be a nonempty string")
    if item.status not in NOTEABLE:
        raise ConflictError(f"Cannot note item in status {item.status}")
    notes = [*item.notes, note.strip()]
    return ExceptionItem(
        item_id=item.item_id,
        tenant_id=item.tenant_id,
        merchant_ref=item.merchant_ref,
        kind=item.kind,
        amount_minor=item.amount_minor,
        currency=item.currency,
        status=item.status,
        notes=notes,
        case_id=item.case_id,
        transaction_ref=item.transaction_ref,
        assignee=item.assignee,
    )


def apply_escalate(item: ExceptionItem, *, reason_code: str) -> ExceptionItem:
    """Escalate keeps monetary/resolution authority elsewhere; never closes as resolved."""
    if not reason_code or not reason_code.strip():
        raise ValidationError("reason_code must be a nonempty string")
    if item.status not in ESCALATABLE:
        raise ConflictError(f"Cannot escalate item in status {item.status}")
    notes = [*item.notes, f"escalated:{reason_code.strip()}"]
    return ExceptionItem(
        item_id=item.item_id,
        tenant_id=item.tenant_id,
        merchant_ref=item.merchant_ref,
        kind=item.kind,
        amount_minor=item.amount_minor,
        currency=item.currency,
        status="ESCALATED",
        notes=notes,
        case_id=item.case_id,
        transaction_ref=item.transaction_ref,
        assignee=item.assignee,
    )


def assert_escalation_not_resolution(item: ExceptionItem) -> None:
    if item.status == "CLOSED":
        raise ConflictError("Escalation must not mark CLOSED as resolved")
    if item.status != "ESCALATED":
        raise ConflictError("Escalated item must have status ESCALATED")


def matches_filters(
    item: ExceptionItem,
    *,
    kind: ExceptionKind | None,
    status: ExceptionStatus | None,
) -> bool:
    if kind is not None and item.kind != kind:
        return False
    if status is not None and item.status != status:
        return False
    return True
