"""Case: provider unavailable → PEER_UNAVAILABLE."""

from sentinel_evidence.adapters.provider_stub import UNAVAILABLE, StubPaymentProvider

PROVIDER = StubPaymentProvider(case=UNAVAILABLE)
