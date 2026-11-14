"""Identity: malformed membership response."""

from sentinel_merchant_teams.adapters.identity_stub import StubIdentityMemberships

PROVIDER = StubIdentityMemberships(mode="malformed")
