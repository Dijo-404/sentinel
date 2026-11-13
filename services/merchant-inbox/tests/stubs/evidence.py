"""evidence.v1 local doubles (valid / unavailable / malformed / unauthorized)."""

from sentinel_merchant_inbox.adapters.local_peers import LocalEvidence, StubMode

StubEvidence = LocalEvidence

__all__ = ["StubEvidence", "StubMode"]
