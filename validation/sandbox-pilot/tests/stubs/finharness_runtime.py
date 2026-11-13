from __future__ import annotations

from stubs._base import PeerStub


class FinharnessRuntimeStub(PeerStub):
    def __init__(self, case: str = "valid") -> None:
        super().__init__(
            port="finharness-runtime.v1",
            case=case,
            component="stub-finharness-runtime",
        )
