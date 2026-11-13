"""harness-telemetry.v1 — sanitized runtime/evaluation hooks and audit correlation."""

from .contracts import (
    CONTRACT_SHA256,
    CONTRACT_VERSION,
    PORT,
    ArtifactRef,
    AuditCorrelationRecord,
    CheckResult,
    FinancialAuditRecord,
    HarnessCorrelation,
    HarnessTelemetryContractError,
    PeerError,
    RedactionError,
    RunInput,
    RunReport,
)
from .hooks import SafeHarnessHooks
from .memory import FailingExporter, MemoryCollector, MemoryFinancialAudit, MissingExporter
from .producers import produce_harness_journey, produce_with_failing_telemetry
from .redaction import sanitize_attributes, sanitize_metric_labels
from .run import run

__all__ = [
    "CONTRACT_SHA256",
    "CONTRACT_VERSION",
    "PORT",
    "ArtifactRef",
    "AuditCorrelationRecord",
    "CheckResult",
    "FailingExporter",
    "FinancialAuditRecord",
    "HarnessCorrelation",
    "HarnessTelemetryContractError",
    "MemoryCollector",
    "MemoryFinancialAudit",
    "MissingExporter",
    "PeerError",
    "RedactionError",
    "RunInput",
    "RunReport",
    "SafeHarnessHooks",
    "produce_harness_journey",
    "produce_with_failing_telemetry",
    "run",
    "sanitize_attributes",
    "sanitize_metric_labels",
]
