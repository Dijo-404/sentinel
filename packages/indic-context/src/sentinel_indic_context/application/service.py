"""Propose use case: normalize, call Sarvam port, validate, preserve provenance."""

from __future__ import annotations

from sentinel_indic_context.application.errors import ForbiddenError, UnauthorizedError
from sentinel_indic_context.application.ports import SarvamPort
from sentinel_indic_context.domain.normalize import normalize_complaint
from sentinel_indic_context.domain.types import (
    InferenceReport,
    ModelRequest,
    ModelResult,
    NormalizedComplaint,
    Principal,
)
from sentinel_indic_context.domain.validate import validate_proposal


class IndicContextService:
    """Models propose only. No ledger writes, approvals, or money movement."""

    def __init__(self, model: SarvamPort, *, native_review_limit: str) -> None:
        self._model = model
        self._native_review_limit = native_review_limit

    def normalize(self, request: ModelRequest) -> NormalizedComplaint:
        return normalize_complaint(request.input)

    def propose(
        self, request: ModelRequest, principal: Principal
    ) -> tuple[ModelResult, InferenceReport, NormalizedComplaint]:
        authorize_propose(principal, request.case.case_id)
        normalized = normalize_complaint(request.input)

        # Ambiguous amount/count claims escalate before any financial proposal.
        if normalized.amount_ambiguous:
            result = ModelResult(
                outcome="NEEDS_INPUT",
                proposal=None,
                reason_codes=["AMOUNT_AMBIGUOUS"],
                original_text=request.input.original_text,
                language=request.input.language,
            )
            report = InferenceReport(
                evidence_mode="fake-inference"
                if self._model.evidence_mode == "fake-inference"
                else "provider-observation",
                model_id=self._model.label,
                latency_ms=0,
                cost_units=0.0,
                native_review_limit=self._native_review_limit,
                outcome=result.outcome,
                reason_codes=list(result.reason_codes),
            )
            return result, report, normalized

        raw_result, report = self._model.propose(request)
        # Provenance: never let the adapter rewrite customer text/language.
        preserved = ModelResult(
            outcome=raw_result.outcome,
            proposal=raw_result.proposal,
            reason_codes=list(raw_result.reason_codes),
            original_text=request.input.original_text,
            language=request.input.language,
        )

        if preserved.outcome == "PROPOSAL":
            failures = validate_proposal(preserved.proposal, request)
            if failures:
                failed = ModelResult(
                    outcome="ESCALATE",
                    proposal=None,
                    reason_codes=failures,
                    original_text=request.input.original_text,
                    language=request.input.language,
                )
                failed_report = report.model_copy(
                    update={
                        "outcome": failed.outcome,
                        "reason_codes": list(failed.reason_codes),
                        "native_review_limit": self._native_review_limit,
                    }
                )
                return failed, failed_report, normalized

        final_report = report.model_copy(
            update={
                "outcome": preserved.outcome,
                "reason_codes": list(preserved.reason_codes),
                "native_review_limit": self._native_review_limit,
            }
        )
        return preserved, final_report, normalized


def authorize_propose(principal: Principal, case_id: str) -> None:
    if "workflow" not in principal.roles:
        raise ForbiddenError("workflow role required")
    if "*" not in principal.case_ids and case_id not in principal.case_ids:
        raise ForbiddenError("case not in principal scope")
    if not principal.principal_id or not principal.tenant_id:
        raise UnauthorizedError("principal incomplete")
