"""Case: evidence peer returns malformed payload."""

from sentinel_merchant_disputes.adapters.peers_fixture import FixtureEvidence

PEER = FixtureEvidence(behavior="malformed")
