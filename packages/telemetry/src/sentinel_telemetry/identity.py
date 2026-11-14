"""Identity-oriented span/metric names and helpers (docs/roles.md §15).

Financial audit (action-ledger) is unsampled and authoritative for money.
Identity audit (invite/role/session) is a separate authoritative family.
Neither is replaced by sampled OTel metrics or this helper surface.

Metric labels stay bounded and non-identifying: no emails, user IDs,
tokens, invitation secrets, or other PII in label keys or values.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from .contracts import CorrelationIds, RecordedSpan, RedactionError
from .ports import TelemetryHooks

# --- §15.1 span names ---------------------------------------------------------

SPAN_SESSION_AUTHENTICATE = "identity.session.authenticate"
SPAN_WORKSPACE_RESOLVE = "identity.workspace.resolve"
SPAN_STAFF_INVITE = "identity.staff.invite"
SPAN_ROLE_ASSIGN = "identity.role.assign"
SPAN_ROLE_REVOKE = "identity.role.revoke"
SPAN_SESSION_REVOKE = "identity.session.revoke"

IDENTITY_SPAN_NAMES: frozenset[str] = frozenset(
    {
        SPAN_SESSION_AUTHENTICATE,
        SPAN_WORKSPACE_RESOLVE,
        SPAN_STAFF_INVITE,
        SPAN_ROLE_ASSIGN,
        SPAN_ROLE_REVOKE,
        SPAN_SESSION_REVOKE,
    }
)

# --- §15.2 metric names -------------------------------------------------------

METRIC_LOGIN_ATTEMPTS_TOTAL = "identity_login_attempts_total"
METRIC_STAFF_INVITATIONS_TOTAL = "identity_staff_invitations_total"
METRIC_ROLE_CHANGES_TOTAL = "identity_role_changes_total"
METRIC_AUTHZ_DENIED_TOTAL = "identity_authz_denied_total"
METRIC_SESSION_REVOCATION_LATENCY_SECONDS = "identity_session_revocation_latency_seconds"

IDENTITY_METRIC_NAMES: frozenset[str] = frozenset(
    {
        METRIC_LOGIN_ATTEMPTS_TOTAL,
        METRIC_STAFF_INVITATIONS_TOTAL,
        METRIC_ROLE_CHANGES_TOTAL,
        METRIC_AUTHZ_DENIED_TOTAL,
        METRIC_SESSION_REVOCATION_LATENCY_SECONDS,
    }
)

# Bounded label values — keep cardinality low; reject free-form strings.
BOUNDED_ROLES: frozenset[str] = frozenset(
    {
        "customer",
        "merchant",
        "operator",
        "supervisor",
        "risk_officer",
        "platform_admin",
        "unknown",
    }
)
BOUNDED_RESULTS: frozenset[str] = frozenset(
    {
        "success",
        "failure",
        "denied",
        "challenged",
        "expired",
        "revoked",
        "rate_limited",
    }
)
BOUNDED_ROLE_OPERATIONS: frozenset[str] = frozenset({"assign", "revoke"})
BOUNDED_AUTHZ_REASONS: frozenset[str] = frozenset(
    {
        "missing_permission",
        "role_mismatch",
        "tenant_mismatch",
        "session_revoked",
        "suspended",
        "authz_version_stale",
        "mfa_required",
        "other",
    }
)
BOUNDED_ENVIRONMENTS: frozenset[str] = frozenset({"sandbox", "fixture", "prod", "unknown"})
# Permission IDs: dotted catalog tokens (docs/roles.md §9.1), not free text.
_PERMISSION_RE = re.compile(r"^[a-z][a-z0-9_.]{0,63}$")

# Keys whose *values* are bounded only via sanitize_identity_metric_labels / emit_*.
IDENTITY_VALUE_BOUNDED_LABEL_KEYS: frozenset[str] = frozenset(
    {"role", "result", "operation", "permission", "reason"}
)

IDENTITY_METRIC_LABEL_KEYS: frozenset[str] = frozenset(
    {
        "service",
        "environment",
        *IDENTITY_VALUE_BOUNDED_LABEL_KEYS,
    }
)


def identity_request_correlation(request_id: str) -> CorrelationIds:
    """Correlation for identity-only paths: request_id only; other slots empty."""
    if not isinstance(request_id, str) or not request_id or len(request_id) > 128:
        raise RedactionError("identity request_id must be a nonempty string up to 128 characters")
    return CorrelationIds(
        request_id=request_id,
        case_id="",
        approval_id="",
        worker_id="",
        provider_ref="",
    )


def _require_bound(value: str, allowed: frozenset[str], field: str) -> str:
    if value not in allowed:
        raise RedactionError(f"identity {field} is not on the bounded allowlist")
    return value


def _require_permission(permission: str) -> str:
    if not isinstance(permission, str) or not _PERMISSION_RE.match(permission):
        raise RedactionError("identity permission label must be a bounded catalog token")
    return permission


def _require_environment(environment: str) -> str:
    return _require_bound(environment, BOUNDED_ENVIRONMENTS, "environment")


def _base_labels(environment: str) -> dict[str, str]:
    return {"service": "identity", "environment": _require_environment(environment)}


def sanitize_identity_metric_labels(labels: dict[str, object] | None) -> dict[str, str]:
    """
    Bound identity metric label values (role/result/operation/permission/reason/environment).

    Free-form callers must use this (or emit_* helpers), not sanitize_metric_labels alone:
    general sanitize_metric_labels rejects identity value-bounded keys.
    """
    from .redaction import sanitize_metric_labels

    if labels is None:
        return {}
    cleaned_keys = {
        key: value for key, value in labels.items() if key not in IDENTITY_VALUE_BOUNDED_LABEL_KEYS
    }
    # Validate identity-specific values before merging into key allowlist sanitize.
    role = labels.get("role")
    result = labels.get("result")
    operation = labels.get("operation")
    permission = labels.get("permission")
    reason = labels.get("reason")
    environment = labels.get("environment")

    bounded: dict[str, str] = {}
    if "role" in labels:
        if not isinstance(role, str):
            raise RedactionError("identity role label must be a string")
        bounded["role"] = _require_bound(role, BOUNDED_ROLES, "role")
    if "result" in labels:
        if not isinstance(result, str):
            raise RedactionError("identity result label must be a string")
        bounded["result"] = _require_bound(result, BOUNDED_RESULTS, "result")
    if "operation" in labels:
        if not isinstance(operation, str):
            raise RedactionError("identity operation label must be a string")
        bounded["operation"] = _require_bound(operation, BOUNDED_ROLE_OPERATIONS, "operation")
    if "permission" in labels:
        if not isinstance(permission, str):
            raise RedactionError("identity permission label must be a string")
        bounded["permission"] = _require_permission(permission)
    if "reason" in labels:
        if not isinstance(reason, str):
            raise RedactionError("identity reason label must be a string")
        bounded["reason"] = _require_bound(reason, BOUNDED_AUTHZ_REASONS, "reason")
    if "environment" in labels:
        if not isinstance(environment, str):
            raise RedactionError("identity environment label must be a string")
        cleaned_keys = {**cleaned_keys, "environment": _require_environment(environment)}

    # Key/secret checks for remaining labels (service, environment, …).
    base = sanitize_metric_labels(cleaned_keys)
    return {**base, **bounded}


@dataclass(frozen=True)
class IdentityAuditHint:
    """
    Documentation-only hint: authoritative identity audit events live in the
    identity service (identity_audit_events), not in telemetry export and not
    in the financial audit port.
    """

    family: Literal["identity"] = "identity"
    note: str = (
        "Identity audit is unsampled authoritative state owned by identity.v1. "
        "Financial audit is owned by the action ledger. Telemetry must not replace either."
    )


def emit_session_authenticate(
    hooks: TelemetryHooks,
    *,
    request_id: str,
    role: str,
    result: str,
    environment: str = "sandbox",
) -> RecordedSpan:
    """Span `identity.session.authenticate` + `identity_login_attempts_total`."""
    role = _require_bound(role, BOUNDED_ROLES, "role")
    result = _require_bound(result, BOUNDED_RESULTS, "result")
    labels = {**_base_labels(environment), "role": role, "result": result}
    corr = identity_request_correlation(request_id)
    span = hooks.start_span(SPAN_SESSION_AUTHENTICATE, corr, {"event.kind": "identity"})
    hooks.add_event(span, "identity.session.authenticate.finished", {"event.kind": "identity"})
    hooks.end_span(span)
    hooks.record_metric(METRIC_LOGIN_ATTEMPTS_TOTAL, 1.0, labels)
    return span


def emit_staff_invite(
    hooks: TelemetryHooks,
    *,
    request_id: str,
    result: str,
    environment: str = "sandbox",
) -> RecordedSpan:
    """Span `identity.staff.invite` + `identity_staff_invitations_total`."""
    result = _require_bound(result, BOUNDED_RESULTS, "result")
    labels = {**_base_labels(environment), "result": result}
    corr = identity_request_correlation(request_id)
    span = hooks.start_span(SPAN_STAFF_INVITE, corr, {"event.kind": "identity"})
    hooks.end_span(span)
    hooks.record_metric(METRIC_STAFF_INVITATIONS_TOTAL, 1.0, labels)
    return span


def emit_role_change(
    hooks: TelemetryHooks,
    *,
    request_id: str,
    role: str,
    operation: str,
    environment: str = "sandbox",
) -> RecordedSpan:
    """Span assign/revoke + `identity_role_changes_total`."""
    role = _require_bound(role, BOUNDED_ROLES, "role")
    operation = _require_bound(operation, BOUNDED_ROLE_OPERATIONS, "operation")
    labels = {**_base_labels(environment), "role": role, "operation": operation}
    span_name = SPAN_ROLE_ASSIGN if operation == "assign" else SPAN_ROLE_REVOKE
    corr = identity_request_correlation(request_id)
    span = hooks.start_span(span_name, corr, {"event.kind": "identity", "action.type": operation})
    hooks.end_span(span)
    hooks.record_metric(METRIC_ROLE_CHANGES_TOTAL, 1.0, labels)
    return span


def emit_session_revoke(
    hooks: TelemetryHooks,
    *,
    request_id: str,
    latency_seconds: float,
    environment: str = "sandbox",
) -> RecordedSpan:
    """Span `identity.session.revoke` + revocation latency histogram sample."""
    if latency_seconds < 0 or latency_seconds > 86_400:
        raise RedactionError("identity revocation latency_seconds out of bound")
    labels = _base_labels(environment)
    corr = identity_request_correlation(request_id)
    span = hooks.start_span(SPAN_SESSION_REVOKE, corr, {"event.kind": "identity"})
    hooks.end_span(span)
    hooks.record_metric(
        METRIC_SESSION_REVOCATION_LATENCY_SECONDS,
        float(latency_seconds),
        labels,
    )
    return span


def emit_authz_denied(
    hooks: TelemetryHooks,
    *,
    permission: str,
    reason: str,
    environment: str = "sandbox",
) -> None:
    """Counter `identity_authz_denied_total` with bounded permission/reason labels."""
    permission = _require_permission(permission)
    reason = _require_bound(reason, BOUNDED_AUTHZ_REASONS, "reason")
    labels = {
        **_base_labels(environment),
        "permission": permission,
        "reason": reason,
    }
    hooks.record_metric(METRIC_AUTHZ_DENIED_TOTAL, 1.0, labels)


AdminEvidenceMode = Literal["fixture", "recorded"]
FinGate = Literal["gated_disabled", "shadow_read_only_unavailable"]


@dataclass(frozen=True)
class AdminObservabilityProjection:
    """
    Redacted admin observability/eval health projection.

    Never invents live queue depths, login rates, or FinHarness/FinBench scores.
    M5/M8 FinHarness and FinBench stay gated until independently enabled.
    """

    evidence_mode: AdminEvidenceMode
    identity_spans_documented: bool
    identity_metrics_documented: bool
    finharness: FinGate
    finbench: FinGate
    live_stats: None
    notes: tuple[str, ...]


def project_admin_observability_health(
    *,
    evidence_mode: AdminEvidenceMode = "fixture",
    finharness_enabled: bool = False,
    finbench_enabled: bool = False,
) -> AdminObservabilityProjection:
    """
    Gated admin health stub for `/admin/observability` and `/admin/evaluations`.

    When FinHarness/FinBench flags are false (default), gates stay disabled.
    When true, still reports unavailable until a real assembled peer exists —
    no fake live statistics.
    """
    finharness: FinGate = "shadow_read_only_unavailable" if finharness_enabled else "gated_disabled"
    finbench: FinGate = "shadow_read_only_unavailable" if finbench_enabled else "gated_disabled"
    notes = (
        "Identity helpers expose span/metric names only; no live scrape in this package.",
        "Financial audit ≠ identity audit ≠ sampled telemetry.",
        "Metric labels must stay bounded; no PII.",
        "FinHarness/FinBench remain independently gated (roles.md M5/M8); not claimed complete.",
    )
    return AdminObservabilityProjection(
        evidence_mode=evidence_mode,
        identity_spans_documented=True,
        identity_metrics_documented=True,
        finharness=finharness,
        finbench=finbench,
        live_stats=None,
        notes=notes,
    )
