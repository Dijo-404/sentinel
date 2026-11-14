from ._base import PeerStub


def identity_stub(case: str = "valid") -> PeerStub:
    return PeerStub(port="identity.v1", case=case, component="stub-identity")
