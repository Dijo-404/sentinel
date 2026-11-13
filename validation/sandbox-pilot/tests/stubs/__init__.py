"""Local peer doubles for consumed ports."""

from stubs.core_assembly import CoreAssemblyStub
from stubs.finbench import FinbenchStub
from stubs.finharness_runtime import FinharnessRuntimeStub
from stubs.harness_replay import HarnessReplayStub
from stubs.harness_telemetry import HarnessTelemetryStub

STUB_CASES = ("valid", "unavailable", "malformed", "unauthorized_or_out_of_scope")

PORT_STUBS = {
    "core-assembly.v1": CoreAssemblyStub,
    "finharness-runtime.v1": FinharnessRuntimeStub,
    "finbench.v1": FinbenchStub,
    "harness-telemetry.v1": HarnessTelemetryStub,
    "harness-replay.v1": HarnessReplayStub,
}

__all__ = [
    "STUB_CASES",
    "PORT_STUBS",
    "CoreAssemblyStub",
    "FinharnessRuntimeStub",
    "FinbenchStub",
    "HarnessTelemetryStub",
    "HarnessReplayStub",
]
