from ._base import PeerStub


def verifier_stub(case: str = "valid") -> PeerStub:
    return PeerStub(port="verifier.v1", case=case, component="stub-verifier")
