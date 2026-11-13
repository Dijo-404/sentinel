from ._base import PeerStub


def action_ledger_stub(case: str = "valid") -> PeerStub:
    return PeerStub(port="action-ledger.v1", case=case, component="stub-action-ledger")
