"""Case: evidence peer returns malformed payload."""

from sentinel_merchant_settlement.adapters.evidence_stub import CASE_MALFORMED, StubEvidence

EVIDENCE = StubEvidence(case=CASE_MALFORMED)
