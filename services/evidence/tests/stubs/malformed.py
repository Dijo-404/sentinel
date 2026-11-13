"""Case: provider returns malformed payload → PEER_MALFORMED."""

from sentinel_evidence.adapters.provider_stub import MALFORMED, StubPaymentProvider

PROVIDER = StubPaymentProvider(case=MALFORMED)
