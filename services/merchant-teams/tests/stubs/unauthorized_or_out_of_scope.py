"""Case: unauthorized or out-of-scope case-api.v1 peer."""

from .case_api import StubCaseApi

PROVIDER = StubCaseApi(mode="unauthorized_or_out_of_scope")
