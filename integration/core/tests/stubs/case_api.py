from ._base import PeerStub


def case_api_stub(case: str = "valid") -> PeerStub:
    return PeerStub(port="case-api.v1", case=case, component="stub-case-api")
