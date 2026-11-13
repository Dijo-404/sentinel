"""Case: payment provider returns malformed payload."""

from sentinel_merchant_settlement.adapters.provider_stub import CASE_MALFORMED, StubPaymentProvider

PROVIDER = StubPaymentProvider(case=CASE_MALFORMED)
