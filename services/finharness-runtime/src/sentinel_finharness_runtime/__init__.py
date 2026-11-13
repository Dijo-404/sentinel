"""finharness-runtime.v1 — pinned-case shadow/sandbox harness runtime."""

from .application.runtime import FinHarnessRuntime, build_runtime
from .domain.errors import (
    CapabilityDenied,
    ConfigurationError,
    ContractViolation,
    PeerError,
    SafetyViolation,
)
from .domain.models import (
    CONTRACT_SHA256,
    CONTRACT_VERSION,
    PORT,
    CaseManifest,
    RuntimeConfig,
    ShadowComparison,
)

__all__ = [
    "CONTRACT_SHA256",
    "CONTRACT_VERSION",
    "PORT",
    "CapabilityDenied",
    "CaseManifest",
    "ConfigurationError",
    "ContractViolation",
    "FinHarnessRuntime",
    "PeerError",
    "RuntimeConfig",
    "SafetyViolation",
    "ShadowComparison",
    "build_runtime",
]
