"""Case: evidence unauthorized or out of scope."""

from sentinel_merchant_disputes.adapters.peers_fixture import FixtureEvidence

PEER = FixtureEvidence(behavior="unauthorized_or_out_of_scope")
