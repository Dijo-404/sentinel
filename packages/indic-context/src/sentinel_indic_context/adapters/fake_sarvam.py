"""Labeled fake Sarvam reasoning. Not a live provider observation."""

from __future__ import annotations

import time
from typing import Any

from sentinel_indic_context.application.errors import ProviderUnavailableError
from sentinel_indic_context.domain.types import InferenceReport, ModelRequest, ModelResult


class FakeSarvamAdapter:
    """Reproducible recorded outputs and injected malformed/malicious proposals."""

    label = "fake-sarvam"
    evidence_mode = "fake-inference"

    def __init__(self, scenario: str = "proposal", policy_version: str = "demo-policy-v1") -> None:
        self.scenario = scenario
        self.policy_version = policy_version

    def propose(self, request: ModelRequest) -> tuple[ModelResult, InferenceReport]:
        started = time.perf_counter()
        if self.scenario == "outage":
            raise ProviderUnavailableError("fake Sarvam outage scenario")

        result = self._build(request)
        latency_ms = int((time.perf_counter() - started) * 1000)
        report = InferenceReport(
            evidence_mode="fake-inference",
            model_id=self.label,
            latency_ms=latency_ms,
            cost_units=0.0,
            prompt_tokens=0,
            completion_tokens=0,
            native_review_limit="human-review-required-for-refunds",
            outcome=result.outcome,
            reason_codes=list(result.reason_codes),
        )
        return result, report

    def _build(self, request: ModelRequest) -> ModelResult:
        original = request.input.original_text
        language = request.input.language
        ids = [e.evidence_id for e in request.evidence]

        if self.scenario == "needs_input":
            return ModelResult(
                outcome="NEEDS_INPUT",
                proposal=None,
                reason_codes=["AMBIGUOUS_TRANSACTION"],
                original_text=original,
                language=language,
            )
        if self.scenario == "escalate":
            return ModelResult(
                outcome="ESCALATE",
                proposal=None,
                reason_codes=["FRAUD_SIGNAL"],
                original_text=original,
                language=language,
            )
        if self.scenario == "malformed":
            return ModelResult(
                outcome="PROPOSAL",
                proposal={"action": "REQUEST_REFUND", "amount_minor": "not-an-int"},
                reason_codes=["DUPLICATE_PAYMENT"],
                original_text=original,
                language=language,
            )
        if self.scenario == "hallucinated_ref":
            return ModelResult(
                outcome="PROPOSAL",
                proposal=self._refund_payload(
                    request,
                    transaction_ref="TXN-DOES-NOT-EXIST",
                    evidence_ids=ids[:1] or ["evidence-payment-b"],
                ),
                reason_codes=["DUPLICATE_PAYMENT"],
                original_text=original,
                language=language,
            )
        if self.scenario == "prompt_injection":
            # Customer text already contains injection; also emit a proposal that must fail.
            return ModelResult(
                outcome="PROPOSAL",
                proposal=self._refund_payload(
                    request,
                    transaction_ref=_first_txn(request) or "TXN-B",
                    evidence_ids=ids[:1] or ["evidence-payment-b"],
                ),
                reason_codes=["DUPLICATE_PAYMENT"],
                original_text=original,
                language=language,
            )
        if self.scenario == "unsupported_action":
            return ModelResult(
                outcome="PROPOSAL",
                proposal={
                    "action": "EXECUTE_DIRECT_REFUND",
                    "case_id": request.case.case_id,
                    "case_revision": request.input.case_revision,
                    "transaction_ref": "TXN-B",
                    "amount_minor": 150000,
                    "currency": "INR",
                    "destination": "ORIGINAL_PAYMENT_ROUTE",
                    "evidence_ids": ids[:1] or ["evidence-payment-b"],
                    "policy_version": self.policy_version,
                },
                reason_codes=["UNSUPPORTED"],
                original_text=original,
                language=language,
            )

        # Default proposal: refund TXN-B using scoped verified evidence.
        txn = _first_txn(request) or "TXN-B"
        evidence_ids = [eid for eid in ("evidence-payment-b", "evidence-order") if eid in set(ids)]
        if not evidence_ids:
            evidence_ids = ids[:2] or ["evidence-payment-b"]
        return ModelResult(
            outcome="PROPOSAL",
            proposal=self._refund_payload(request, transaction_ref=txn, evidence_ids=evidence_ids),
            reason_codes=["DUPLICATE_PAYMENT"],
            original_text=original,
            language=language,
        )

    def _refund_payload(
        self,
        request: ModelRequest,
        *,
        transaction_ref: str,
        evidence_ids: list[str],
    ) -> dict[str, Any]:
        return {
            "action": "REQUEST_REFUND",
            "case_id": request.case.case_id,
            "case_revision": request.input.case_revision,
            "transaction_ref": transaction_ref,
            "amount_minor": 150000,
            "currency": "INR",
            "destination": "ORIGINAL_PAYMENT_ROUTE",
            "evidence_ids": evidence_ids,
            "policy_version": self.policy_version,
        }


def _first_txn(request: ModelRequest) -> str | None:
    for item in request.evidence:
        payment = (item.facts or {}).get("payment")
        if isinstance(payment, dict) and isinstance(payment.get("transaction_ref"), str):
            return payment["transaction_ref"]
    return None
