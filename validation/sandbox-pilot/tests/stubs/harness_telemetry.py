from __future__ import annotations

from stubs._base import PeerStub


class HarnessTelemetryStub(PeerStub):
    def __init__(self, case: str = "valid") -> None:
        super().__init__(
            port="harness-telemetry.v1",
            case=case,
            component="stub-harness-telemetry",
        )
