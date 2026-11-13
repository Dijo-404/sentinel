from __future__ import annotations

from stubs._base import PeerStub


class CoreAssemblyStub(PeerStub):
    def __init__(self, case: str = "valid") -> None:
        super().__init__(
            port="core-assembly.v1",
            case=case,
            component="stub-core-assembly",
        )
