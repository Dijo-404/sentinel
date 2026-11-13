"""In-process case-api.v1 / evidence.v1 doubles for fixture mode."""

from __future__ import annotations

import json
from pathlib import Path

from ..application.errors import (
    PeerMalformedError,
    PeerUnauthorizedError,
    PeerUnavailableError,
)
from ..domain.aggregates import parse_rfc3339
from ..domain.types import CaseRecord, Principal, RefundFact

_ROOT = Path(__file__).resolve().parents[3]
_FIXTURES = _ROOT / "fixtures"


def load_fixture_cases() -> list[CaseRecord]:
    raw = json.loads((_FIXTURES / "cases.json").read_text(encoding="utf-8"))
    rows: list[CaseRecord] = []
    for item in raw["cases"]:
        rows.append(
            CaseRecord(
                case_id=item["case_id"],
                merchant_ref=item["merchant_ref"],
                status=item["status"],
                intent=item["intent"],
                opened_at=item["opened_at"],
                closed_at=item.get("closed_at"),
                evidence_ids=tuple(item.get("evidence_ids", [])),
                currency=item.get("currency", "INR"),
            )
        )
    return rows


def load_fixture_refunds() -> list[RefundFact]:
    raw = json.loads((_FIXTURES / "evidence.json").read_text(encoding="utf-8"))
    rows: list[RefundFact] = []
    for item in raw["refunds"]:
        rows.append(
            RefundFact(
                case_id=item["case_id"],
                amount_minor=item["amount_minor"],
                currency=item["currency"],
                status=item["status"],
                observed_at=item["observed_at"],
            )
        )
    return rows


class FixtureCaseApi:
    """valid / unavailable / malformed / unauthorized_or_out_of_scope selectors."""

    def __init__(self, behavior: str = "valid", cases: list[CaseRecord] | None = None) -> None:
        self.behavior = behavior
        self._cases = cases if cases is not None else load_fixture_cases()

    def list_merchant_cases(
        self,
        principal: Principal,
        *,
        merchant_ref: str,
        window_start: str,
        window_end: str,
    ) -> list[CaseRecord]:
        if self.behavior == "unavailable":
            raise PeerUnavailableError("Required peer unavailable")
        if self.behavior == "malformed":
            raise PeerMalformedError("Case peer response malformed")
        if self.behavior == "unauthorized_or_out_of_scope":
            raise PeerUnauthorizedError("Case peer denied scoped read")
        start = parse_rfc3339(window_start)
        end = parse_rfc3339(window_end)
        out: list[CaseRecord] = []
        for case in self._cases:
            if case.merchant_ref != merchant_ref:
                continue
            if not principal.allows_case(case.case_id) and "*" not in principal.case_ids:
                continue
            opened = parse_rfc3339(case.opened_at)
            if start <= opened <= end:
                out.append(case)
        return out


class FixtureEvidence:
    def __init__(self, behavior: str = "valid", refunds: list[RefundFact] | None = None) -> None:
        self.behavior = behavior
        self._refunds = refunds if refunds is not None else load_fixture_refunds()

    def list_refund_facts(
        self,
        principal: Principal,
        *,
        case_ids: list[str],
    ) -> list[RefundFact]:
        del principal
        if self.behavior == "unavailable":
            raise PeerUnavailableError("Required peer unavailable")
        if self.behavior == "malformed":
            raise PeerMalformedError("Evidence peer response malformed")
        if self.behavior == "unauthorized_or_out_of_scope":
            raise PeerUnauthorizedError("Evidence peer denied scoped read")
        wanted = set(case_ids)
        return [r for r in self._refunds if r.case_id in wanted]
