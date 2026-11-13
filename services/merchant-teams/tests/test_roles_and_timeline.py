"""Role assignment and append-only activity timeline."""

from __future__ import annotations

from tests.conftest import OPERATOR


def test_role_assignment_and_append_only_timeline(service, store):
    service.create(
        OPERATOR,
        merchant_ref="merchant-demo-1",
        display_name="Bo",
        roles=["viewer"],
        staff_id="staff-bo",
    )
    service.update(OPERATOR, "staff-bo", roles=["operator", "approver"])
    service.record_activity(
        OPERATOR,
        "staff-bo",
        kind="NOTE",
        subject_ref="merchant-demo-1",
        summary="Reviewed queue",
    )

    events = service.list_activity(OPERATOR, "staff-bo")
    kinds = [event.kind for event in events]
    assert kinds == ["STAFF_CREATED", "ROLE_ASSIGNED", "NOTE"]
    assert all(event.at == "2026-11-13T12:00:00Z" for event in events)

    # Append-only: prior event payloads stay immutable.
    first = events[0]
    store.append_activity(first)
    again = service.list_activity(OPERATOR, "staff-bo")
    assert again[0] == first
    assert len(again) == 4


def test_case_activity_uses_case_api(service):
    service.create(
        OPERATOR,
        merchant_ref="merchant-demo-1",
        display_name="Casey",
        roles=["operator"],
        staff_id="staff-casey",
    )
    event = service.record_activity(
        OPERATOR,
        "staff-casey",
        kind="CASE_VIEW",
        subject_ref="case-demo-42",
        summary="Opened case",
    )
    assert event.kind == "CASE_VIEW"
    assert event.subject_ref == "case-demo-42"
