"""case-api.v1 local doubles."""

from __future__ import annotations

from typing import Literal

from sentinel_merchant_refunds import CONTRACT_VERSION
from sentinel_merchant_refunds.domain.errors import PeerError, PeerUnavailableError
from sentinel_merchant_refunds.domain.types import CaseRecord, Principal

StubMode = Literal["valid", "unavailable", "malformed", "unauthorized_or_out_of_scope"]


class StubCaseApi:
    def __init__(self, *, mode: StubMode = "valid", revision: int = 1) -> None:
        self.mode = mode
        self.revision = revision
        self.calls = 0

    def get_case(self, principal: Principal, case_id: str) -> CaseRecord:
        del principal
        self.calls += 1
        self._guard()
        if self.mode == "malformed":
            raise PeerError("MALFORMED_PEER", "Malformed case-api response", status_code=502)
        return CaseRecord(
            contract_version=CONTRACT_VERSION,
            case_id=case_id,
            revision=self.revision,
            status="INVESTIGATING",
            language="en-IN",
            intent="DUPLICATE_PAYMENT",
            evidence_ids=[],
        )

    def _guard(self) -> None:
        if self.mode == "unavailable":
            raise PeerUnavailableError("case-api")
        if self.mode == "unauthorized_or_out_of_scope":
            raise PeerError("FORBIDDEN", "Unauthorized or out of scope", status_code=403)
