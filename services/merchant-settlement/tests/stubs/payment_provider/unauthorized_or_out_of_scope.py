"""Case: payment provider unauthorized / out of scope."""

from sentinel_merchant_settlement.adapters.provider_stub import (
    CASE_UNAUTHORIZED,
    StubPaymentProvider,
)

PROVIDER = StubPaymentProvider(case=CASE_UNAUTHORIZED)
