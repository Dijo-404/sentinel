"""Local identity.v1 membership doubles for SN-039 standalone checks."""

from sentinel_merchant_teams.adapters.identity_stub import StubIdentityMemberships

from .malformed import PROVIDER as MALFORMED
from .unauthorized_or_out_of_scope import PROVIDER as UNAUTHORIZED
from .unavailable import PROVIDER as UNAVAILABLE
from .valid import PROVIDER as VALID

__all__ = [
    "StubIdentityMemberships",
    "VALID",
    "UNAVAILABLE",
    "MALFORMED",
    "UNAUTHORIZED",
]
