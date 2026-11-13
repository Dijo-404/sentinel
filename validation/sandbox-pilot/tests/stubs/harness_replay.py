from __future__ import annotations

from stubs._base import PeerStub


class HarnessReplayStub(PeerStub):
    def __init__(self, case: str = "valid") -> None:
        super().__init__(
            port="harness-replay.v1",
            case=case,
            component="stub-harness-replay",
        )
