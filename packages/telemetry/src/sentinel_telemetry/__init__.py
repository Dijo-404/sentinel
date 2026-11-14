"""telemetry.v1 — sanitized OTel hooks, redaction, bounded metrics, local examples."""

from .contracts import (
    CONTRACT_SHA256,
    CONTRACT_VERSION,
    PORT,
    ArtifactRef,
    CheckResult,
    CorrelationIds,
    FinancialAuditRecord,
    RedactionError,
    RunInput,
    RunReport,
    TelemetryContractError,
)
from .hooks import FailingSink, SafeTelemetryHooks
from .identity import (
    IDENTITY_METRIC_NAMES,
    IDENTITY_SPAN_NAMES,
    AdminObservabilityProjection,
    IdentityAuditHint,
    emit_authz_denied,
    emit_role_change,
    emit_session_authenticate,
    emit_session_revoke,
    emit_staff_invite,
    project_admin_observability_health,
    sanitize_identity_metric_labels,
)
from .memory import MemoryCollector, MemoryFinancialAudit
from .producers import produce_correlated_journey, produce_with_failing_telemetry
from .redaction import sanitize_attributes, sanitize_metric_labels
from .run import run

__all__ = [
    "CONTRACT_SHA256",
    "CONTRACT_VERSION",
    "PORT",
    "AdminObservabilityProjection",
    "ArtifactRef",
    "CheckResult",
    "CorrelationIds",
    "FailingSink",
    "FinancialAuditRecord",
    "IDENTITY_METRIC_NAMES",
    "IDENTITY_SPAN_NAMES",
    "IdentityAuditHint",
    "MemoryCollector",
    "MemoryFinancialAudit",
    "RedactionError",
    "RunInput",
    "RunReport",
    "SafeTelemetryHooks",
    "TelemetryContractError",
    "emit_authz_denied",
    "emit_role_change",
    "emit_session_authenticate",
    "emit_session_revoke",
    "emit_staff_invite",
    "produce_correlated_journey",
    "produce_with_failing_telemetry",
    "project_admin_observability_health",
    "run",
    "sanitize_attributes",
    "sanitize_identity_metric_labels",
    "sanitize_metric_labels",
]
