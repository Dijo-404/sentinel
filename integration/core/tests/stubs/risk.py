from ._base import PeerStub


def risk_stub(case: str = "valid") -> PeerStub:
    return PeerStub(port="risk.v1", case=case, component="stub-risk")
