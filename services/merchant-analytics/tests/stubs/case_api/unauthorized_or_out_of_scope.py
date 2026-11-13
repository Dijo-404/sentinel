"""Case: case-api peer denies scoped read."""

from sentinel_merchant_analytics.adapters.fixture_peers import FixtureCaseApi

CASE_API = FixtureCaseApi(behavior="unauthorized_or_out_of_scope")
