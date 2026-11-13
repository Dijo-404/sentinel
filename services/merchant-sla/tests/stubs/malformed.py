"""Case: malformed case-api.v1 peer."""

from sentinel_merchant_sla.adapters.case_api_fixture import FixtureCaseApi

PROVIDER = FixtureCaseApi(behavior="malformed")
