"""Local peer doubles for case-api.v1 and evidence.v1."""

from sentinel_merchant_inbox.adapters.local_peers import LocalCaseApi, LocalEvidence

StubCaseApi = LocalCaseApi
StubEvidence = LocalEvidence

__all__ = ["StubCaseApi", "StubEvidence", "LocalCaseApi", "LocalEvidence"]
