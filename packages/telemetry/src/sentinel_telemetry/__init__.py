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
from .memory import MemoryCollector, MemoryFinancialAudit
from .producers import produce_correlated_journey, produce_with_failing_telemetry
from .redaction import sanitize_attributes, sanitize_metric_labels
from .run import run

__all__ = [
    "CONTRACT_SHA256",
    "CONTRACT_VERSION",
    "PORT",
    "ArtifactRef",
    "CheckResult",
    "CorrelationIds",
    "FailingSink",
    "FinancialAuditRecord",
    "MemoryCollector",
    "MemoryFinancialAudit",
    "RedactionError",
    "RunInput",
    "RunReport",
    "SafeTelemetryHooks",
    "TelemetryContractError",
    "produce_correlated_journey",
    "produce_with_failing_telemetry",
    "run",
    "sanitize_attributes",
    "sanitize_metric_labels",
]
