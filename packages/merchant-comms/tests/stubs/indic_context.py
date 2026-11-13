"""indic-context.v1 stub cases: valid, unavailable, malformed, unauthorized_or_out_of_scope."""

from sentinel_merchant_comms.adapters.fixture_peers import (
    FixtureIndicContext,
    MalformedIndicContext,
    UnauthorizedIndicContext,
    UnavailableIndicContext,
)

ValidIndicContext = FixtureIndicContext

__all__ = [
    "ValidIndicContext",
    "UnavailableIndicContext",
    "MalformedIndicContext",
    "UnauthorizedIndicContext",
]
