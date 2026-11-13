"""In-process fixture peers for local/fixture mode. Clearly not real services."""

from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from sentinel_workflow.application.errors import PeerError, PeerUnavailableError
from sentinel_workflow.domain.digest import action_digest
from sentinel_workflow.domain.types import (
    ActionRecord,
    Approval,
    Case,
    CaseInput,
    CaseMessage,
    CaseResult,
    Evidence,
    EvidenceBundle,
    PolicyRequest,
    PolicyResult,
    ProposalRequest,
    RefundAction,
    ReservationRequest,
    VerificationRequest,
    VerificationResult,
)

Behavior = Literal["valid", "unavailable", "malformed", "unauthorized_or_out_of_scope"]


def _now() -> datetime:
    return datetime.now(UTC)


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


class FixtureCaseApi:
    def __init__(self, behavior: Behavior = "valid") -> None:
        self.behavior = behavior
        self.results: list[CaseResult] = []
        self._revision = 1
        self._status = "RECEIVED"
        self._action_id: str | None = None
        self.fail_submit_times = 0
        self.submit_conflict: str | None = None

    def get_input(self, case_id: str, revision: int) -> CaseInput:
        self._guard()
        if self.behavior == "malformed":
            raise PeerError("MALFORMED", "malformed case input", 502)
        return CaseInput(
            case_id=case_id,
            case_revision=revision,
            original_text="I was charged twice for order DEMO-ORDER-42",
            language="en-IN",
            order_reference="DEMO-ORDER-42",
            messages=[
                CaseMessage(
                    message_id="msg-1",
                    text="I was charged twice for order DEMO-ORDER-42",
                    language="en-IN",
                    author="CUSTOMER",
                    occurred_at="2026-11-13T10:00:00Z",
                )
            ],
        )

    def get_case(self, case_id: str) -> Case:
        self._guard()
        if self.behavior == "malformed":
            raise PeerError("MALFORMED", "malformed case", 502)
        body: dict[str, Any] = {
            "contract_version": "sentinel.task-contracts.v1",
            "case_id": case_id,
            "revision": self._revision,
            "status": self._status,
            "language": "en-IN",
            "intent": "DUPLICATE_PAYMENT",
            "evidence_ids": [],
        }
        if self._action_id:
            body["action_id"] = self._action_id
        return Case.model_validate(body)

    def submit_result(self, case_id: str, result: CaseResult) -> Case:
        self._guard()
        if self.fail_submit_times > 0:
            self.fail_submit_times -= 1
            raise PeerUnavailableError("case-api")
        if self.submit_conflict == "IDEMPOTENCY_CONFLICT":
            raise PeerError("IDEMPOTENCY_CONFLICT", "event_key conflict", 409)
        if self.submit_conflict == "REVISION_CONFLICT":
            raise PeerError("REVISION_CONFLICT", "stale revision", 409)
        for prior in self.results:
            if prior.event_key == result.event_key:
                if prior.model_dump(exclude_none=True) != result.model_dump(exclude_none=True):
                    raise PeerError("IDEMPOTENCY_CONFLICT", "event_key conflict", 409)
                return self.get_case(case_id)
        if result.expected_revision != self._revision:
            raise PeerError("REVISION_CONFLICT", "stale revision", 409)
        self.results.append(result)
        self._revision += 1
        self._status = result.status
        self._action_id = result.action_id
        return self.get_case(case_id)

    def _guard(self) -> None:
        if self.behavior == "unavailable":
            raise PeerUnavailableError("case-api")
        if self.behavior == "unauthorized_or_out_of_scope":
            raise PeerError("UNAUTHORIZED", "out of scope", 403)


class FixtureEvidence:
    def __init__(self, behavior: Behavior = "valid", *, missing: bool = False) -> None:
        self.behavior = behavior
        self.missing = missing

    def collect(self, case_id: str, case_revision: int, order_reference: str) -> EvidenceBundle:
        del case_revision, order_reference
        if self.behavior == "unavailable":
            raise PeerUnavailableError("evidence")
        if self.behavior == "unauthorized_or_out_of_scope":
            raise PeerError("UNAUTHORIZED", "out of scope", 403)
        if self.behavior == "malformed":
            raise PeerError("MALFORMED", "malformed evidence", 502)
        if self.missing:
            return EvidenceBundle(
                case_id=case_id, evidence=[], reconciliation_codes=["MISSING_EVIDENCE"]
            )
        observed = _now()
        expires = observed + timedelta(hours=1)
        evidence = [
            Evidence(
                evidence_id="evidence-payment-a",
                case_id=case_id,
                source="simulator",
                subject_ref="subject-demo",
                observed_at=_iso(observed),
                expires_at=_iso(expires),
                digest="a" * 64,
                verification_status="VERIFIED",
                facts={
                    "kind": "PAYMENT",
                    "payment": {
                        "transaction_ref": "TXN-A",
                        "order_reference": "DEMO-ORDER-42",
                        "subject_ref": "subject-demo",
                        "status": "CAPTURED",
                        "amount_minor": 150000,
                        "currency": "INR",
                    },
                },
            ),
            Evidence(
                evidence_id="evidence-payment-b",
                case_id=case_id,
                source="simulator",
                subject_ref="subject-demo",
                observed_at=_iso(observed),
                expires_at=_iso(expires),
                digest="b" * 64,
                verification_status="VERIFIED",
                facts={
                    "kind": "PAYMENT",
                    "payment": {
                        "transaction_ref": "TXN-B",
                        "order_reference": "DEMO-ORDER-42",
                        "subject_ref": "subject-demo",
                        "status": "CAPTURED",
                        "amount_minor": 150000,
                        "currency": "INR",
                    },
                },
            ),
            Evidence(
                evidence_id="evidence-order",
                case_id=case_id,
                source="simulator",
                subject_ref="subject-demo",
                observed_at=_iso(observed),
                expires_at=_iso(expires),
                digest="c" * 64,
                verification_status="VERIFIED",
                facts={
                    "kind": "ORDER",
                    "order": {
                        "order_reference": "DEMO-ORDER-42",
                        "subject_ref": "subject-demo",
                        "fulfilled_order_count": 1,
                        "merchant_confirmed_duplicate": True,
                        "paid": True,
                    },
                },
            ),
        ]
        return EvidenceBundle(
            case_id=case_id,
            evidence=evidence,
            reconciliation_codes=["DUPLICATE_CAPTURED_PAYMENT"],
        )


class FixturePolicy:
    def __init__(self, behavior: Behavior = "valid") -> None:
        self.behavior = behavior

    def evaluate(self, request: PolicyRequest) -> PolicyResult:
        if self.behavior == "unavailable":
            raise PeerUnavailableError("policy")
        if self.behavior == "unauthorized_or_out_of_scope":
            raise PeerError("UNAUTHORIZED", "out of scope", 403)
        if self.behavior == "malformed":
            raise PeerError("MALFORMED", "malformed policy", 502)
        digest = action_digest(request.payload)
        if request.payload.get("action") == "REQUEST_REFUND":
            if request.approval and request.approval.decision == "APPROVE":
                if request.approval.action_digest != digest:
                    return PolicyResult(
                        outcome="DENY",
                        reason_codes=["DIGEST_MISMATCH"],
                        policy_version="demo-policy-v1",
                        action_digest=digest,
                        required_evidence=[],
                    )
                return PolicyResult(
                    outcome="ALLOW",
                    reason_codes=["APPROVED"],
                    policy_version="demo-policy-v1",
                    action_digest=digest,
                    required_evidence=[],
                )
            return PolicyResult(
                outcome="REQUIRE_APPROVAL",
                reason_codes=["SUPERVISOR_REQUIRED"],
                policy_version="demo-policy-v1",
                action_digest=digest,
                required_evidence=[],
            )
        return PolicyResult(
            outcome="ALLOW",
            reason_codes=["OK"],
            policy_version="demo-policy-v1",
            action_digest=digest,
            required_evidence=[],
        )


class FixtureLedger:
    def __init__(self, behavior: Behavior = "valid") -> None:
        self.behavior = behavior
        self.by_operation: dict[str, ActionRecord] = {}
        self.proposal_calls = 0
        self.reserve_calls = 0

    def create_proposal(self, request: ProposalRequest) -> ActionRecord:
        self._guard()
        existing = self.by_operation.get(request.operation_key)
        if existing is not None:
            if existing.action_digest != request.action_digest:
                raise PeerError("CONFLICT", "operation_key conflict", 409)
            return deepcopy(existing)
        self.proposal_calls += 1
        action_id = f"action-{len(self.by_operation) + 1}"
        provider_ref = f"refund-{len(self.by_operation) + 1}"
        record = ActionRecord(
            action_id=action_id,
            provider_ref=provider_ref,
            payload=request.payload,
            action_digest=request.action_digest,
            status="PROPOSED",
        )
        self.by_operation[request.operation_key] = record
        return deepcopy(record)

    def reserve(self, request: ReservationRequest) -> ActionRecord:
        self._guard()
        existing = self.by_operation.get(request.operation_key)
        if existing is None:
            existing = self.create_proposal(
                ProposalRequest(
                    operation_key=request.operation_key,
                    payload=request.payload,
                    action_digest=request.action_digest,
                )
            )
        if existing.status == "RESERVED" and existing.approval is not None:
            if existing.approval.approval_id != request.approval_id:
                raise PeerError("CONFLICT", "approval mismatch", 409)
            return deepcopy(existing)
        self.reserve_calls += 1
        approval = Approval(
            approval_id=request.approval_id,
            action_digest=request.action_digest,
            case_revision=request.payload.case_revision,
            policy_version=request.payload.policy_version,
            decision="APPROVE",
            reviewer_id="supervisor-demo",
            expires_at=_iso(_now() + timedelta(hours=1)),
        )
        updated = ActionRecord(
            action_id=existing.action_id,
            provider_ref=existing.provider_ref,
            payload=request.payload
            if isinstance(request.payload, RefundAction)
            else RefundAction.model_validate(request.payload),
            action_digest=request.action_digest,
            status="RESERVED",
            approval=approval,
        )
        self.by_operation[request.operation_key] = updated
        return deepcopy(updated)

    def get_action(self, action_id: str) -> ActionRecord:
        self._guard()
        for record in self.by_operation.values():
            if record.action_id == action_id:
                return deepcopy(record)
        raise PeerError("NOT_FOUND", "action not found", 404)

    def attach_approval(self, action_id: str, approval: Approval) -> ActionRecord:
        for key, record in self.by_operation.items():
            if record.action_id == action_id:
                updated = ActionRecord(
                    action_id=record.action_id,
                    provider_ref=record.provider_ref,
                    payload=record.payload,
                    action_digest=record.action_digest,
                    status=record.status,
                    approval=approval,
                )
                self.by_operation[key] = updated
                return deepcopy(updated)
        raise PeerError("NOT_FOUND", "action not found", 404)

    def _guard(self) -> None:
        if self.behavior == "unavailable":
            raise PeerUnavailableError("action-ledger")
        if self.behavior == "unauthorized_or_out_of_scope":
            raise PeerError("UNAUTHORIZED", "out of scope", 403)
        if self.behavior == "malformed":
            raise PeerError("MALFORMED", "malformed ledger", 502)


class FixtureVerifier:
    def __init__(self, behavior: Behavior = "valid", assessment_status: str = "WAITING") -> None:
        self.behavior = behavior
        self.assessment_status = assessment_status
        self.rechecks: list[str] = []

    def schedule_recheck(self, request: VerificationRequest, idempotency_key: str) -> str:
        del request
        self._guard()
        if idempotency_key not in self.rechecks:
            self.rechecks.append(idempotency_key)
        return f"job-{idempotency_key}"

    def assess(self, request: VerificationRequest) -> VerificationResult:
        self._guard()
        return VerificationResult(
            assessment_id=f"assess-{request.action_id}",
            case_id=request.case_id,
            case_revision=request.case_revision,
            action_id=request.action_id,
            assessed_at=_iso(_now()),
            expires_at=_iso(_now() + timedelta(hours=1)),
            status=self.assessment_status,  # type: ignore[arg-type]
            evidence=[],
            reason_codes=["PENDING_PROVIDER"]
            if self.assessment_status == "WAITING"
            else ["CREDIT_CONFIRMED"],
        )

    def _guard(self) -> None:
        if self.behavior == "unavailable":
            raise PeerUnavailableError("verifier")
        if self.behavior == "unauthorized_or_out_of_scope":
            raise PeerError("UNAUTHORIZED", "out of scope", 403)
        if self.behavior == "malformed":
            raise PeerError("MALFORMED", "malformed verifier", 502)
