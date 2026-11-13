"""Case: evidence peer unavailable."""

from sentinel_merchant_disputes.adapters.peers_fixture import FixtureEvidence

PEER = FixtureEvidence(behavior="unavailable")
