"""Case: valid scoped provider payments/orders."""

from sentinel_merchant_settlement.adapters.provider_stub import CASE_VALID, StubPaymentProvider

PROVIDER = StubPaymentProvider(case=CASE_VALID)
