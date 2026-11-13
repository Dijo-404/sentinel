from __future__ import annotations

from stubs._base import PeerStub


class FinbenchStub(PeerStub):
    def __init__(self, case: str = "valid") -> None:
        super().__init__(
            port="finbench.v1",
            case=case,
            component="stub-finbench",
        )
