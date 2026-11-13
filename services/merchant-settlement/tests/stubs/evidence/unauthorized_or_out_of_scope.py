"""Case: evidence peer unauthorized / out of scope."""

from sentinel_merchant_settlement.adapters.evidence_stub import CASE_UNAUTHORIZED, StubEvidence

EVIDENCE = StubEvidence(case=CASE_UNAUTHORIZED)
