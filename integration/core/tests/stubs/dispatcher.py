from ._base import PeerStub


def dispatcher_stub(case: str = "valid") -> PeerStub:
    return PeerStub(port="dispatcher.v1", case=case, component="stub-dispatcher")
