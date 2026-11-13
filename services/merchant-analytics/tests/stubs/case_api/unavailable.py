"""Case: case-api peer unavailable."""

from sentinel_merchant_analytics.adapters.fixture_peers import FixtureCaseApi

CASE_API = FixtureCaseApi(behavior="unavailable")
