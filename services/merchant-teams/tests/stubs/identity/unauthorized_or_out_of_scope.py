"""Identity: unauthorized or out-of-scope membership read."""

from sentinel_merchant_teams.adapters.identity_stub import StubIdentityMemberships

PROVIDER = StubIdentityMemberships(mode="unauthorized_or_out_of_scope")
