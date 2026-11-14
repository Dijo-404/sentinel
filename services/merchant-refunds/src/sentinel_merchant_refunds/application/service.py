"""Merchant refund request lifecycle. Ledger/policy own financial authority."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sentinel_merchant_refunds.application.ports import (
    CaseApiPort,
    Clock,
    EvidencePort,
    IdGenerator,
    LedgerPort,
    PolicyPort,
    RequestStore,
)
from sentinel_merchant_refunds.domain.digest import action_digest
from sentinel_merchant_refunds.domain.errors import (
    ConflictError,
    NotFoundError,
    UnauthorizedError,
    ValidationError,
)
from sentinel_merchant_refunds.domain.status import map_ledger_status
from sentinel_merchant_refunds.domain.types import (
    ApprovalDecision,
    DraftCreate,
    DraftUpdate,
    MerchantRefundRequest,
    Principal,
    ProposalRequest,
    RefundActionPayload,
    ReservationRequest,
)

DEMO_POLICY_VERSION = "demo-policy-v1"


@dataclass
class MerchantRefundService:
    store: RequestStore
    case_api: CaseApiPort
    evidence: EvidencePort
    policy: PolicyPort
    ledger: LedgerPort
    clock: Clock
    ids: IdGenerator

    def create_draft(
        self,
        principal: Principal,
        body: DraftCreate,
        *,
        idempotency_key: str,
    ) -> MerchantRefundRequest:
        self._require_merchant(principal)
        existing = self.store.get_by_idempotency(principal.tenant_id, idempotency_key)
        if existing is not None:
            if self._draft_fingerprint(existing) != self._create_fingerprint(body, principal):
                raise ConflictError("Idempotency-Key conflicts with stored draft")
            return existing
        request = MerchantRefundRequest(
            request_id=self.ids.new_id("mrr"),
            tenant_id=principal.tenant_id,
            merchant_ref=principal.merchant_ref,
            case_id=body.case_id,
            transaction_ref=body.transaction_ref,
            amount_minor=body.amount_minor,
            currency=body.currency,
            evidence_ids=list(body.evidence_ids),
            rationale=body.rationale,
            status="DRAFT",
        )
        self.store.put(request)
        self.store.put_idempotency(principal.tenant_id, idempotency_key, request)
        return request

    def get(self, principal: Principal, request_id: str) -> MerchantRefundRequest:
        self._require_merchant(principal)
        request = self._load(principal, request_id)
        return request

    def update_draft(
        self, principal: Principal, request_id: str, body: DraftUpdate
    ) -> MerchantRefundRequest:
        self._require_merchant(principal)
        request = self._load(principal, request_id)
        if request.status != "DRAFT":
            raise ConflictError("Only DRAFT requests can be updated")
        updates: dict = {}
        if body.transaction_ref is not None:
            updates["transaction_ref"] = body.transaction_ref
        if body.amount_minor is not None:
            updates["amount_minor"] = body.amount_minor
        if body.currency is not None:
            updates["currency"] = body.currency
        if body.evidence_ids is not None:
            updates["evidence_ids"] = list(body.evidence_ids)
        if body.rationale is not None:
            updates["rationale"] = body.rationale
        updated = request.model_copy(update=updates)
        self.store.put(updated)
        return updated

    def submit(self, principal: Principal, request_id: str) -> MerchantRefundRequest:
        """Submit draft through evidence + policy + ledger proposal ports only."""
        self._require_merchant(principal)
        request = self._load(principal, request_id)
        if request.status not in {"DRAFT", "SUBMITTED"}:
            raise ConflictError("Request is not submittable")
        if not request.evidence_ids:
            raise ValidationError("evidence_ids required before submit")

        case = self.case_api.get_case(principal, request.case_id)
        evidence_objects = self._selected_evidence(principal, request)

        payload = RefundActionPayload(
            case_id=request.case_id,
            case_revision=case.revision,
            transaction_ref=request.transaction_ref,
            amount_minor=request.amount_minor,
            currency=request.currency,  # type: ignore[arg-type]
            evidence_ids=list(request.evidence_ids),
            policy_version=DEMO_POLICY_VERSION,
        )
        digest = action_digest(payload.as_dict())
        policy_result = self.policy.evaluate(
            principal,
            payload=payload.as_dict(),
            evidence=evidence_objects,
        )
        if policy_result.action_digest != digest:
            raise ValidationError("Policy action_digest mismatch")

        operation_key = f"merchant-refund:{principal.tenant_id}:{request.request_id}"
        base = request.model_copy(
            update={
                "status": "SUBMITTED",
                "case_revision": case.revision,
                "policy_version": policy_result.policy_version,
                "action_digest": digest,
                "operation_key": operation_key,
                # Never forge action_id locally.
                "action_id": None,
                "approval_id": None,
                "ledger_status": None,
            }
        )

        if policy_result.outcome == "DENY":
            rejected = base.model_copy(update={"status": "REJECTED"})
            self.store.put(rejected)
            return rejected

        if policy_result.outcome == "NEED_EVIDENCE":
            raise ValidationError(
                "Additional evidence required: " + ",".join(policy_result.required_evidence)
            )

        if policy_result.outcome == "REQUIRE_APPROVAL":
            # action_id comes only from ledger response.
            record = self.ledger.create_proposal(
                principal,
                ProposalRequest(
                    operation_key=operation_key,
                    payload=payload.as_dict(),
                    action_digest=digest,
                ),
            )
            awaiting = base.model_copy(
                update={
                    "status": "AWAITING_APPROVAL",
                    "action_id": record.action_id,
                    "ledger_status": record.status,
                }
            )
            self.store.put(awaiting)
            return awaiting

        if policy_result.outcome == "ALLOW":
            # ALLOW without a bound approval cannot reserve money.
            raise ValidationError("ALLOW without approval_id cannot reserve; use decision path")

        raise ValidationError(f"Unsupported policy outcome: {policy_result.outcome}")

    def apply_decision(
        self, principal: Principal, request_id: str, decision: ApprovalDecision
    ) -> MerchantRefundRequest:
        self._require_merchant(principal)
        request = self._load(principal, request_id)
        if request.status != "AWAITING_APPROVAL":
            raise ConflictError("Decision allowed only for AWAITING_APPROVAL")
        if request.action_id is None or request.action_digest is None:
            raise ValidationError("Missing ledger proposal for decision")
        if request.operation_key is None or request.case_revision is None:
            raise ValidationError("Missing operation context for decision")
        if decision.action_digest != request.action_digest:
            raise ValidationError("Approval action_digest mismatch")
        if self._expired(decision.expires_at):
            raise ValidationError("Approval expired")

        if decision.decision == "REJECT":
            rejected = request.model_copy(
                update={"status": "REJECTED", "approval_id": decision.approval_id}
            )
            self.store.put(rejected)
            return rejected

        payload = RefundActionPayload(
            case_id=request.case_id,
            case_revision=request.case_revision,
            transaction_ref=request.transaction_ref,
            amount_minor=request.amount_minor,
            currency=request.currency,  # type: ignore[arg-type]
            evidence_ids=list(request.evidence_ids),
            policy_version=decision.policy_version,
        )
        approval_body = {
            "approval_id": decision.approval_id,
            "action_digest": decision.action_digest,
            "case_revision": decision.case_revision,
            "policy_version": decision.policy_version,
            "decision": decision.decision,
            "reviewer_id": decision.reviewer_id,
            "expires_at": decision.expires_at,
        }
        evidence_objects = self._selected_evidence(principal, request)
        policy_result = self.policy.evaluate(
            principal,
            payload=payload.as_dict(),
            evidence=evidence_objects,
            approval=approval_body,
        )
        if policy_result.outcome == "DENY":
            denied = request.model_copy(
                update={"status": "REJECTED", "approval_id": decision.approval_id}
            )
            self.store.put(denied)
            return denied
        if policy_result.outcome != "ALLOW":
            raise ValidationError(f"Approved decision expected ALLOW, got {policy_result.outcome}")

        # Reservation authority stays on the ledger. No local action_id minting.
        prior_action_id = request.action_id
        record = self.ledger.reserve(
            principal,
            ReservationRequest(
                operation_key=request.operation_key,
                payload=payload.as_dict(),
                action_digest=request.action_digest,
                approval_id=decision.approval_id,
            ),
        )
        if record.action_id != prior_action_id:
            raise ConflictError("Ledger returned unexpected action_id on reserve")
        reserved = request.model_copy(
            update={
                "status": "RESERVED",
                "action_id": record.action_id,
                "approval_id": decision.approval_id,
                "ledger_status": record.status,
                "policy_version": policy_result.policy_version,
            }
        )
        self.store.put(reserved)
        return reserved

    def sync(self, principal: Principal, request_id: str) -> MerchantRefundRequest:
        """Refresh local status from ledger. PENDING never becomes VERIFIED."""
        self._require_merchant(principal)
        request = self._load(principal, request_id)
        if request.action_id is None:
            raise ValidationError("No action_id to sync; request never reached ledger")
        if request.status in {"DRAFT", "REJECTED"}:
            raise ConflictError("Nothing to sync for this status")
        record = self.ledger.get_action(principal, request.action_id)
        mapped = map_ledger_status(record.status)
        updated = request.model_copy(
            update={
                "status": mapped,
                "ledger_status": record.status,
                "action_id": record.action_id,
            }
        )
        self.store.put(updated)
        return updated

    def _selected_evidence(
        self, principal: Principal, request: MerchantRefundRequest
    ) -> list[dict]:
        """Load, validate, and return policy.v1 evidence objects for request ids."""
        bundle = self.evidence.get_case_evidence(principal, request.case_id)
        by_id = {item.evidence_id: item for item in bundle.evidence}
        now = self.clock.now_iso()
        selected: list[dict] = []
        for evidence_id in request.evidence_ids:
            item = by_id.get(evidence_id)
            if item is None:
                raise ValidationError(f"Unknown evidence_id: {evidence_id}")
            if item.case_id != request.case_id:
                raise UnauthorizedError("Evidence out of case scope")
            if item.verification_status != "VERIFIED":
                raise ValidationError(f"Evidence not VERIFIED: {evidence_id}")
            if item.expires_at <= now:
                raise ValidationError(f"Evidence expired: {evidence_id}")
            selected.append(item.model_dump())
        return selected

    def _load(self, principal: Principal, request_id: str) -> MerchantRefundRequest:
        request = self.store.get(principal.tenant_id, request_id)
        if request is None:
            raise NotFoundError("Refund request not found")
        if (
            request.tenant_id != principal.tenant_id
            or request.merchant_ref != principal.merchant_ref
        ):
            raise UnauthorizedError("Refund request out of scope")
        return request

    def _require_merchant(self, principal: Principal) -> None:
        if not principal.tenant_id or not principal.merchant_ref:
            raise UnauthorizedError("Merchant principal required")
        if "merchant_staff" not in principal.roles and "merchant_supervisor" not in principal.roles:
            raise UnauthorizedError("Merchant role required")

    def _expired(self, expires_at: str) -> bool:
        return expires_at <= self.clock.now_iso()

    @staticmethod
    def _create_fingerprint(body: DraftCreate, principal: Principal) -> tuple:
        return (
            principal.tenant_id,
            principal.merchant_ref,
            body.case_id,
            body.transaction_ref,
            body.amount_minor,
            body.currency,
            tuple(body.evidence_ids),
            body.rationale,
        )

    @staticmethod
    def _draft_fingerprint(request: MerchantRefundRequest) -> tuple:
        return (
            request.tenant_id,
            request.merchant_ref,
            request.case_id,
            request.transaction_ref,
            request.amount_minor,
            request.currency,
            tuple(request.evidence_ids),
            request.rationale,
        )


def parse_rfc3339(value: str) -> datetime:
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return datetime.fromisoformat(value)
