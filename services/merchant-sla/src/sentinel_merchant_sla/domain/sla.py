"""SLA due dates, overdue flags, and task status transitions."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sentinel_merchant_sla.contracts import (
    RESOLVED_CASE_STATUSES,
    TASK_STATUSES,
    SlaInputError,
    SlaPolicy,
    SlaTarget,
    TaskStatus,
)


def parse_rfc3339(value: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise SlaInputError("INVALID_INPUT", "timestamps must be UTC RFC 3339 ending in Z")
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    except ValueError as exc:
        raise SlaInputError("INVALID_INPUT", f"invalid timestamp: {value}") from exc


def format_rfc3339(instant: datetime) -> str:
    if instant.tzinfo is None:
        instant = instant.replace(tzinfo=UTC)
    return instant.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def compute_due_at(
    *,
    policy: SlaPolicy,
    target: SlaTarget,
    opened_at: datetime,
) -> datetime:
    seconds = (
        policy.respond_within_seconds if target == "respond" else policy.resolve_within_seconds
    )
    return opened_at + timedelta(seconds=seconds)


def compute_overdue(*, status: TaskStatus, due_at: datetime, now: datetime) -> bool:
    if status == "DONE":
        return False
    return now >= due_at


def is_financially_resolved(case_status: str | None) -> bool:
    """Escalation is a handoff, never verified financial resolution."""
    if case_status is None:
        return False
    return case_status in RESOLVED_CASE_STATUSES


def validate_follow_up_at(*, follow_up_at: str, now: datetime) -> datetime:
    instant = parse_rfc3339(follow_up_at)
    if instant < now:
        raise SlaInputError("INVALID_INPUT", "follow_up_at must not be earlier than now")
    return instant


def transition_assign(status: TaskStatus) -> TaskStatus:
    if status == "DONE":
        raise SlaInputError("CONFLICT", "cannot assign a DONE task")
    if status == "ESCALATED":
        return "ESCALATED"
    return "IN_PROGRESS"


def transition_escalate(status: TaskStatus) -> TaskStatus:
    if status == "DONE":
        raise SlaInputError("CONFLICT", "cannot escalate a DONE task")
    if status not in TASK_STATUSES:
        raise SlaInputError("INVALID_INPUT", f"unknown status: {status}")
    # Escalation is never DONE and never financial resolution.
    return "ESCALATED"


def transition_complete(status: TaskStatus) -> TaskStatus:
    if status == "DONE":
        return "DONE"
    if status not in TASK_STATUSES:
        raise SlaInputError("INVALID_INPUT", f"unknown status: {status}")
    return "DONE"
