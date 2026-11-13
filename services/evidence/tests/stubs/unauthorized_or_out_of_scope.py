"""Case: provider denies scoped read → PEER_UNAUTHORIZED."""

from sentinel_evidence.adapters.provider_stub import UNAUTHORIZED, StubPaymentProvider

PROVIDER = StubPaymentProvider(case=UNAUTHORIZED)
