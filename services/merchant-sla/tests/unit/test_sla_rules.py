"""Domain and use-case acceptance: overdue, follow-ups, escalate≠done."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from tests.stubs import valid

from sentinel_merchant_sla.adapters.clock import FixedClock
from sentinel_merchant_sla.adapters.memory_store import MemorySlaStore
from sentinel_merchant_sla.application.errors import ConflictError
from sentinel_merchant_sla.application.service import MerchantSlaService
from sentinel_merchant_sla.contracts import Principal, SlaPolicy
from sentinel_merchant_sla.domain.sla import (
    compute_due_at,
    compute_overdue,
    is_financially_resolved,
    transition_escalate,
)

T0 = datetime(2026, 11, 13, 10, 0, 0, tzinfo=UTC)
PRINCIPAL = Principal(
    principal_id="op-merchant-demo",
    tenant_id="demo-tenant-a",
    roles=("operator", "merchant_ops"),
    subject_refs=("subject-demo-42",),
    case_ids=("case-demo-42",),
    merchant_refs=("merchant-demo-a",),
)


def _service(clock: FixedClock | None = None) -> tuple[MerchantSlaService, FixedClock]:
    clk = clock or FixedClock(T0)
    svc = MerchantSlaService(store=MemorySlaStore(), clock=clk, case_api=valid())
    return svc, clk


def test_policy_due_dates_and_overdue_virtual_clock():
    policy = SlaPolicy(
        policy_id="p1",
        tenant_id="demo-tenant-a",
        merchant_ref="merchant-demo-a",
        respond_within_seconds=900,
        resolve_within_seconds=3600,
    )
    due = compute_due_at(policy=policy, target="resolve", opened_at=T0)
    assert due.isoformat().replace("+00:00", "Z") == "2026-11-13T11:00:00Z"
    assert compute_overdue(status="OPEN", due_at=due, now=T0) is False
    assert compute_overdue(status="OPEN", due_at=due, now=due) is True
    assert compute_overdue(status="DONE", due_at=due, now=due) is False


def test_service_overdue_and_follow_up_against_virtual_clock():
    svc, clock = _service()
    policy = svc.upsert_policy(
        PRINCIPAL,
        {
            "tenant_id": "demo-tenant-a",
            "merchant_ref": "merchant-demo-a",
            "respond_within_seconds": 900,
            "resolve_within_seconds": 3600,
        },
    )
    task = svc.create_task(
        PRINCIPAL,
        {"case_id": "case-demo-42", "policy_id": policy.policy_id, "target": "resolve"},
    )
    assert task.overdue is False
    assert task.due_at == "2026-11-13T11:00:00Z"
    assert task.status == "OPEN"

    clock.advance(seconds=3600)
    refreshed = svc.get_task(PRINCIPAL, task.task_id)
    assert refreshed.overdue is True

    follow = svc.schedule_follow_up(
        PRINCIPAL,
        task.task_id,
        {"follow_up_at": "2026-11-13T12:00:00Z"},
    )
    assert follow.follow_up_at == "2026-11-13T12:00:00Z"
    assert follow.overdue is True


def test_escalation_is_not_done_and_not_financial_resolution():
    assert transition_escalate("OPEN") == "ESCALATED"
    assert transition_escalate("IN_PROGRESS") == "ESCALATED"
    assert is_financially_resolved("ESCALATED") is False
    assert is_financially_resolved("VERIFIED_RESOLVED") is True

    svc, clock = _service()
    policy = svc.upsert_policy(
        PRINCIPAL,
        {
            "tenant_id": "demo-tenant-a",
            "merchant_ref": "merchant-demo-a",
            "respond_within_seconds": 60,
            "resolve_within_seconds": 120,
        },
    )
    task = svc.create_task(
        PRINCIPAL,
        {
            "case_id": "case-demo-42",
            "policy_id": policy.policy_id,
            "target": "respond",
            "assignee": "op-merchant-demo",
        },
    )
    clock.advance(seconds=120)
    escalated = svc.escalate_task(
        PRINCIPAL,
        task.task_id,
        {"reason_code": "SLA_BREACH", "owner_queue": "merchant-ops"},
    )
    assert escalated.status == "ESCALATED"
    assert escalated.status != "DONE"
    assert escalated.case_status == "ESCALATED"
    assert escalated.financially_resolved is False
    assert escalated.overdue is True

    done = svc.complete_task(PRINCIPAL, task.task_id)
    assert done.status == "DONE"
    assert done.overdue is False
    assert done.financially_resolved is False
    assert done.case_status == "ESCALATED"


def test_cannot_follow_up_after_done():
    svc, _clock = _service()
    policy = svc.upsert_policy(
        PRINCIPAL,
        {
            "tenant_id": "demo-tenant-a",
            "merchant_ref": "merchant-demo-a",
            "respond_within_seconds": 60,
            "resolve_within_seconds": 120,
        },
    )
    task = svc.create_task(
        PRINCIPAL,
        {"case_id": "case-demo-42", "policy_id": policy.policy_id},
    )
    svc.complete_task(PRINCIPAL, task.task_id)
    with pytest.raises(ConflictError):
        svc.schedule_follow_up(
            PRINCIPAL,
            task.task_id,
            {"follow_up_at": "2026-11-13T12:00:00Z"},
        )
