"""Optional finharness-sdk.v1: injectable ports, pinned manifests, disabled-by-default routing."""

from .client import FinHarnessClient
from .config import ExecutionMode, RuntimeConfig
from .contracts import (
    CONTRACT_SHA256,
    CONTRACT_VERSION,
    PORT,
    CapabilityDenied,
    ConfigurationError,
    ContractViolation,
    PeerError,
)
from .manifest import CaseManifest
from .sample import SampleReport, run_sample_workflow

__all__ = [
    "CONTRACT_SHA256",
    "CONTRACT_VERSION",
    "PORT",
    "CapabilityDenied",
    "CaseManifest",
    "ConfigurationError",
    "ContractViolation",
    "ExecutionMode",
    "FinHarnessClient",
    "PeerError",
    "RuntimeConfig",
    "SampleReport",
    "run_sample_workflow",
]
