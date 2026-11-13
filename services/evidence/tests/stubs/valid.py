"""Case: valid scoped provider facts supporting duplicate reconciliation."""

from sentinel_evidence.adapters.provider_stub import CASE, StubPaymentProvider

PROVIDER = StubPaymentProvider(case=CASE)
