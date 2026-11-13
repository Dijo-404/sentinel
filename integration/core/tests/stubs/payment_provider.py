from ._base import PeerStub


def payment_provider_stub(case: str = "valid") -> PeerStub:
    return PeerStub(port="payment-provider.v1", case=case, component="stub-payment-provider")
