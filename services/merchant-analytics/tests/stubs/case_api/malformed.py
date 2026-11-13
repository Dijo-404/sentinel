"""Case: case-api peer returns malformed payloads."""

from sentinel_merchant_analytics.adapters.fixture_peers import FixtureCaseApi

CASE_API = FixtureCaseApi(behavior="malformed")
