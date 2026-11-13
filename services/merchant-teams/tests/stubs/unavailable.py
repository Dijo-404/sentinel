"""Case: unavailable case-api.v1 peer."""

from .case_api import StubCaseApi

PROVIDER = StubCaseApi(mode="unavailable")
