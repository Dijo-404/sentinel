"""case-api.v1 stub cases: valid, unavailable, malformed, unauthorized_or_out_of_scope."""

from sentinel_merchant_comms.adapters.fixture_peers import (
    FixtureCaseApi,
    MalformedCaseApi,
    UnauthorizedCaseApi,
    UnavailableCaseApi,
)

ValidCaseApi = FixtureCaseApi

__all__ = [
    "ValidCaseApi",
    "UnavailableCaseApi",
    "MalformedCaseApi",
    "UnauthorizedCaseApi",
]
