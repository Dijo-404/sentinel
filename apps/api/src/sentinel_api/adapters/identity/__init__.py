"""Identity principal projection adapters."""

from sentinel_api.adapters.identity.fixture import FixtureIdentityPrincipalAdapter
from sentinel_api.adapters.identity.http import HttpIdentityPrincipalAdapter, principal_from_me

__all__ = [
    "FixtureIdentityPrincipalAdapter",
    "HttpIdentityPrincipalAdapter",
    "principal_from_me",
]
