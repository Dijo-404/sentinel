"""Case: evidence peer denies scoped read."""

from sentinel_merchant_analytics.adapters.fixture_peers import FixtureEvidence

EVIDENCE = FixtureEvidence(behavior="unauthorized_or_out_of_scope")
