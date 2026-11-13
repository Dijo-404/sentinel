"""Case: payment provider unavailable."""

from sentinel_merchant_settlement.adapters.provider_stub import (
    CASE_UNAVAILABLE,
    StubPaymentProvider,
)

PROVIDER = StubPaymentProvider(case=CASE_UNAVAILABLE)
