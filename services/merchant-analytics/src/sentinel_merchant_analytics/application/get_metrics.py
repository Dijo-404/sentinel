"""GetMerchantMetrics use case — read-only aggregation over case/evidence ports."""

from __future__ import annotations

from ..domain.aggregates import compute_metrics, parse_rfc3339
from ..domain.types import MerchantMetrics, Principal
from .errors import UnauthorizedError, ValidationError
from .ports import CaseApiPort, EvidencePort

_ALLOWED_ROLES = frozenset({"operator", "supervisor"})


class GetMerchantMetrics:
    def __init__(self, cases: CaseApiPort, evidence: EvidencePort) -> None:
        self._cases = cases
        self._evidence = evidence

    def __call__(
        self,
        principal: Principal,
        *,
        merchant_ref: str,
        window_start: str,
        window_end: str,
    ) -> MerchantMetrics:
        self._authorize(principal, merchant_ref)
        self._validate_window(window_start, window_end)

        case_rows = self._cases.list_merchant_cases(
            principal,
            merchant_ref=merchant_ref,
            window_start=window_start,
            window_end=window_end,
        )
        case_ids = [c.case_id for c in case_rows]
        refunds = self._evidence.list_refund_facts(principal, case_ids=case_ids)
        return compute_metrics(
            tenant_id=principal.tenant_id,
            merchant_ref=merchant_ref,
            window_start=window_start,
            window_end=window_end,
            cases=case_rows,
            refunds=refunds,
        )

    @staticmethod
    def _authorize(principal: Principal, merchant_ref: str) -> None:
        if not _ALLOWED_ROLES.intersection(principal.roles):
            raise UnauthorizedError("Operator or supervisor role required")
        if not principal.allows_merchant(merchant_ref):
            # Same status/code for unknown merchant — do not leak existence.
            raise UnauthorizedError("Merchant scope denied")

    @staticmethod
    def _validate_window(window_start: str, window_end: str) -> None:
        try:
            start = parse_rfc3339(window_start)
            end = parse_rfc3339(window_end)
        except ValueError as exc:
            raise ValidationError("window_start/window_end must be RFC 3339 UTC") from exc
        if end < start:
            raise ValidationError("window_end must be >= window_start")
