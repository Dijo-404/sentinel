from ._base import PeerStub


def workflow_stub(case: str = "valid") -> PeerStub:
    return PeerStub(port="workflow.v1", case=case, component="stub-workflow")
