"""Baseline structured-model adapters (fake + configurable HTTP)."""

from __future__ import annotations

from typing import Any

import httpx

from sentinel_workflow.application.errors import PeerError, PeerUnavailableError, ValidationError
from sentinel_workflow.domain.digest import action_digest
from sentinel_workflow.domain.types import ModelRequest, ModelResult, RefundAction


class FakeModelAdapter:
    """Labeled fake inference — not a live model. Controlled by scenario name."""

    label = "fake"

    def __init__(self, scenario: str = "proposal", policy_version: str = "demo-policy-v1") -> None:
        self.scenario = scenario
        self.policy_version = policy_version

    def propose(self, request: ModelRequest) -> ModelResult:
        if self.scenario == "outage":
            raise PeerUnavailableError("model")
        if self.scenario == "malformed":
            raise ValidationError("Fake model produced malformed output")
        if self.scenario == "needs_input":
            return ModelResult(
                outcome="NEEDS_INPUT",
                reason_codes=["AMBIGUOUS_TRANSACTION"],
                original_text=request.input.original_text,
                language=request.input.language,
            )
        if self.scenario == "escalate":
            return ModelResult(
                outcome="ESCALATE",
                reason_codes=["FRAUD_SIGNAL"],
                original_text=request.input.original_text,
                language=request.input.language,
            )
        # Default: proposal for duplicate TXN-B refund using verified evidence ids.
        ids = {e.evidence_id for e in request.evidence}
        evidence_ids = [
            eid for eid in ("evidence-payment-b", "evidence-order") if eid in ids or not ids
        ] or [e.evidence_id for e in request.evidence][:2]
        proposal = RefundAction(
            case_id=request.case.case_id,
            case_revision=request.input.case_revision,
            transaction_ref="TXN-B",
            amount_minor=150000,
            evidence_ids=evidence_ids,
            policy_version=self.policy_version,
        )
        # Ensure digest fixture compatibility when using demo evidence ids.
        dump = proposal.model_dump(exclude_none=True)
        _ = action_digest(dump)
        return ModelResult(
            outcome="PROPOSAL",
            proposal=dump,
            reason_codes=["DUPLICATE_PAYMENT"],
            original_text=request.input.original_text,
            language=request.input.language,
        )


class HttpModelAdapter:
    """Configurable real structured-model peer. Failures stay visible — no fixture fallback."""

    label = "http"

    def __init__(self, base_url: str, bearer_token: str, timeout: float = 10.0) -> None:
        if not base_url:
            raise PeerUnavailableError("model")
        self._base = base_url.rstrip("/")
        self._token = bearer_token
        self._timeout = timeout

    def propose(self, request: ModelRequest) -> ModelResult:
        try:
            response = httpx.post(
                f"{self._base}/v1/proposals",
                json=request.model_dump(exclude_none=True),
                headers={"Authorization": f"Bearer {self._token}"},
                timeout=self._timeout,
            )
        except httpx.HTTPError as exc:
            raise PeerUnavailableError("model") from exc
        if response.status_code >= 500:
            raise PeerUnavailableError("model")
        if response.status_code in {401, 403}:
            raise PeerError("UNAUTHORIZED", "Model peer unauthorized", 403)
        if response.status_code >= 400:
            raise PeerError("MODEL_ERROR", f"Model peer returned {response.status_code}", 502)
        try:
            body: dict[str, Any] = response.json()
            return ModelResult.model_validate(body)
        except Exception as exc:
            raise PeerError("MODEL_MALFORMED", "Model peer returned malformed body", 502) from exc
