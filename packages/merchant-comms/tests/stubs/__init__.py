"""Peer stubs for case-api.v1 and indic-context.v1 (valid/unavailable/malformed/unauthorized)."""

from sentinel_merchant_comms.adapters.fixture_peers import (
    FixtureCaseApi,
    FixtureIndicContext,
    MalformedCaseApi,
    MalformedIndicContext,
    UnauthorizedCaseApi,
    UnauthorizedIndicContext,
    UnavailableCaseApi,
    UnavailableIndicContext,
)

ValidCaseApi = FixtureCaseApi
ValidIndicContext = FixtureIndicContext

__all__ = [
    "ValidCaseApi",
    "UnavailableCaseApi",
    "MalformedCaseApi",
    "UnauthorizedCaseApi",
    "ValidIndicContext",
    "UnavailableIndicContext",
    "MalformedIndicContext",
    "UnauthorizedIndicContext",
]
