"""Identity span/metric helpers and gated admin health projection."""

import pytest

from sentinel_telemetry import (
    IDENTITY_METRIC_NAMES,
    IDENTITY_SPAN_NAMES,
    IdentityAuditHint,
    MemoryCollector,
    MemoryFinancialAudit,
    RedactionError,
    SafeTelemetryHooks,
    emit_authz_denied,
    emit_role_change,
    emit_session_authenticate,
    emit_session_revoke,
    emit_staff_invite,
    project_admin_observability_health,
    sanitize_metric_labels,
)
from sentinel_telemetry.identity import (
    METRIC_AUTHZ_DENIED_TOTAL,
    METRIC_LOGIN_ATTEMPTS_TOTAL,
    METRIC_ROLE_CHANGES_TOTAL,
    METRIC_SESSION_REVOCATION_LATENCY_SECONDS,
    METRIC_STAFF_INVITATIONS_TOTAL,
    SPAN_ROLE_ASSIGN,
    SPAN_ROLE_REVOKE,
    SPAN_SESSION_AUTHENTICATE,
    SPAN_SESSION_REVOKE,
    SPAN_STAFF_INVITE,
)


def test_identity_span_and_metric_name_sets() -> None:
    assert SPAN_SESSION_AUTHENTICATE in IDENTITY_SPAN_NAMES
    assert SPAN_STAFF_INVITE in IDENTITY_SPAN_NAMES
    assert SPAN_ROLE_ASSIGN in IDENTITY_SPAN_NAMES
    assert SPAN_ROLE_REVOKE in IDENTITY_SPAN_NAMES
    assert SPAN_SESSION_REVOKE in IDENTITY_SPAN_NAMES
    assert METRIC_LOGIN_ATTEMPTS_TOTAL in IDENTITY_METRIC_NAMES
    assert METRIC_STAFF_INVITATIONS_TOTAL in IDENTITY_METRIC_NAMES
    assert METRIC_ROLE_CHANGES_TOTAL in IDENTITY_METRIC_NAMES
    assert METRIC_AUTHZ_DENIED_TOTAL in IDENTITY_METRIC_NAMES
    assert METRIC_SESSION_REVOCATION_LATENCY_SECONDS in IDENTITY_METRIC_NAMES


def test_emit_session_authenticate_records_span_and_metric() -> None:
    collector = MemoryCollector()
    hooks = SafeTelemetryHooks(collector, collector, failure_log=collector)
    span = emit_session_authenticate(
        hooks, request_id="req-login-1", role="operator", result="success"
    )
    assert span.name == SPAN_SESSION_AUTHENTICATE
    assert any(s.name == SPAN_SESSION_AUTHENTICATE for s in collector.spans)
    assert collector.metrics[-1].name == METRIC_LOGIN_ATTEMPTS_TOTAL
    assert collector.metrics[-1].labels == {
        "service": "identity",
        "environment": "sandbox",
        "role": "operator",
        "result": "success",
    }


def test_emit_staff_invite_and_role_change() -> None:
    collector = MemoryCollector()
    hooks = SafeTelemetryHooks(collector, collector, failure_log=collector)
    emit_staff_invite(hooks, request_id="req-invite-1", result="success")
    emit_role_change(hooks, request_id="req-role-1", role="supervisor", operation="assign")
    emit_role_change(hooks, request_id="req-role-2", role="supervisor", operation="revoke")
    names = {s.name for s in collector.spans}
    assert SPAN_STAFF_INVITE in names
    assert SPAN_ROLE_ASSIGN in names
    assert SPAN_ROLE_REVOKE in names
    metric_names = {m.name for m in collector.metrics}
    assert METRIC_STAFF_INVITATIONS_TOTAL in metric_names
    assert METRIC_ROLE_CHANGES_TOTAL in metric_names


def test_emit_session_revoke_and_authz_denied() -> None:
    collector = MemoryCollector()
    hooks = SafeTelemetryHooks(collector, collector, failure_log=collector)
    emit_session_revoke(hooks, request_id="req-rev-1", latency_seconds=0.25)
    emit_authz_denied(hooks, permission="ledger_approve", reason="missing_permission")
    assert any(s.name == SPAN_SESSION_REVOKE for s in collector.spans)
    latency = next(
        m for m in collector.metrics if m.name == METRIC_SESSION_REVOCATION_LATENCY_SECONDS
    )
    assert latency.value == 0.25
    denied = next(m for m in collector.metrics if m.name == METRIC_AUTHZ_DENIED_TOTAL)
    assert denied.labels["permission"] == "ledger_approve"
    assert denied.labels["reason"] == "missing_permission"


def test_unbounded_identity_labels_rejected_before_hooks() -> None:
    collector = MemoryCollector()
    hooks = SafeTelemetryHooks(collector, collector, failure_log=collector)
    with pytest.raises(RedactionError):
        emit_session_authenticate(hooks, request_id="req-bad", role="superuser", result="success")
    with pytest.raises(RedactionError):
        emit_authz_denied(hooks, permission="a" * 80, reason="other")
    with pytest.raises(RedactionError):
        emit_session_revoke(hooks, request_id="req-bad", latency_seconds=-1)
    assert collector.spans == []
    assert collector.metrics == []


def test_identity_metric_labels_sanitize_and_reject_pii_keys() -> None:
    cleaned = sanitize_metric_labels(
        {
            "service": "identity",
            "environment": "sandbox",
            "role": "customer",
            "result": "denied",
        }
    )
    assert cleaned["role"] == "customer"
    with pytest.raises(RedactionError):
        sanitize_metric_labels({"email": "a@b.c"})
    with pytest.raises(RedactionError):
        sanitize_metric_labels({"user_id": "u-1"})


def test_identity_helpers_do_not_write_financial_audit() -> None:
    collector = MemoryCollector()
    hooks = SafeTelemetryHooks(collector, collector, failure_log=collector)
    audit = MemoryFinancialAudit()
    emit_session_authenticate(hooks, request_id="req-iso-1", role="customer", result="success")
    assert audit.records == []
    hint = IdentityAuditHint()
    assert hint.family == "identity"
    assert "Financial audit" in hint.note


def test_admin_observability_projection_gated_no_live_stats() -> None:
    proj = project_admin_observability_health()
    assert proj.evidence_mode == "fixture"
    assert proj.live_stats is None
    assert proj.finharness == "gated_disabled"
    assert proj.finbench == "gated_disabled"
    assert proj.identity_spans_documented is True
    flagged = project_admin_observability_health(finharness_enabled=True, finbench_enabled=True)
    assert flagged.finharness == "shadow_read_only_unavailable"
    assert flagged.finbench == "shadow_read_only_unavailable"
    assert flagged.live_stats is None
