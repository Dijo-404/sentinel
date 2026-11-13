"""Case: malformed case-api.v1 peer."""

from .case_api import StubCaseApi

PROVIDER = StubCaseApi(mode="malformed")
