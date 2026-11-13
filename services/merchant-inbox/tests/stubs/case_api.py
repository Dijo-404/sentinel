"""case-api.v1 local doubles (valid / unavailable / malformed / unauthorized)."""

from sentinel_merchant_inbox.adapters.local_peers import LocalCaseApi, StubMode

StubCaseApi = LocalCaseApi

__all__ = ["StubCaseApi", "StubMode"]
