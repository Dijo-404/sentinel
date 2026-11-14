"""Use cases: investigations, findings, restriction decisions, dashboard."""

from __future__ import annotations

import uuid
from dataclasses import replace

from ..domain import rules
from ..domain.types import (
    CreateInvestigationRequest,
    DashboardView,
    Finding,
    Investigation,
    Principal,
    RecordFindingRequest,
    RestrictionDecisionRequest,
    ResumeEvent,
    RiskRestriction,
)
from . import errors
from .ports import CaseApiPort, Clock, RiskStore, WorkflowPort

POLICY_VERSION = "risk-policy-v1"


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


class RiskService:
    def __init__(
        self,
        *,
        case_api: CaseApiPort,
        workflow: WorkflowPort,
        store: RiskStore,
        clock: Clock,
    ) -> None:
        self._case_api = case_api
        self._workflow = workflow
        self._store = store
        self._clock = clock

    def create_investigation(
        self,
        principal: Principal,
        request: CreateInvestigationRequest,
        *,
        idempotency_key: str | None = None,
    ) -> Investigation:
        self._require_risk_officer(principal)
        if not request.case_id.strip() or not request.reason_code.strip():
            raise errors.ValidationError("case_id and reason_code are required")
        if not principal.allows_case(request.case_id):
            raise errors.UnauthorizedError("Unauthorized or out of scope")
        if not principal.allows_queue(request.queue_ref):
            raise errors.UnauthorizedError("Unauthorized or out of scope")

        case = self._case_api.get_case(request.case_id, principal=principal)
        if case.case_id != request.case_id:
            raise errors.PeerMalformedError("case-api returned mismatched case_id")
        if request.case_revision is not None:
            case_revision = request.case_revision
        else:
            case_revision = case.revision
        now = self._clock.now()
        created_at = rules.format_rfc3339(now)
        if request.review_due_at:
            try:
                rules.parse_rfc3339(request.review_due_at)
            except ValueError as exc:
                raise errors.ValidationError("review_due_at must be RFC 3339 UTC") from exc
            review_due_at = request.review_due_at
        else:
            review_due_at = rules.default_review_due(now)

        investigation_id = _new_id("inv")
        restriction_id = _new_id("rst")
        investigation = Investigation(
            investigation_id=investigation_id,
            tenant_id=principal.tenant_id,
            case_id=request.case_id,
            case_revision=case_revision,
            reason_code=request.reason_code,
            status="OPEN",
            queue_ref=request.queue_ref,
            owner_principal_id=principal.principal_id,
            severity=request.severity or "MEDIUM",
            created_at=created_at,
            updated_at=created_at,
            revision=1,
            finding_ids=(),
            restriction_ids=(restriction_id,),
            evidence_ids=request.evidence_ids,
        )
        # FLOW-10: fraud investigation starts with an active financial-action block.
        restriction = RiskRestriction(
            restriction_id=restriction_id,
            tenant_id=principal.tenant_id,
            case_id=request.case_id,
            investigation_id=investigation_id,
            reason_code=request.reason_code,
            status="ACTIVE",
            blocks_financial_actions=True,
            created_at=created_at,
            review_due_at=review_due_at,
            created_by=principal.principal_id,
            policy_version=POLICY_VERSION,
            evidence_ids=request.evidence_ids or case.evidence_ids,
            revision=1,
            financial_approval_granted=False,
        )
        return self._store.create_investigation(
            investigation, restriction, idempotency_key=idempotency_key
        )

    def get_investigation(self, principal: Principal, investigation_id: str) -> Investigation:
        investigation = self._require_investigation(investigation_id)
        self._authorize(
            principal,
            investigation.tenant_id,
            investigation.case_id,
            investigation.queue_ref,
        )
        return investigation

    def list_investigations(
        self,
        principal: Principal,
        *,
        case_id: str | None = None,
    ) -> tuple[Investigation, ...]:
        self._require_risk_officer(principal)
        items = self._store.list_investigations(tenant_id=principal.tenant_id, case_id=case_id)
        return tuple(
            item
            for item in items
            if principal.allows_case(item.case_id) and principal.allows_queue(item.queue_ref)
        )

    def dashboard(self, principal: Principal) -> DashboardView:
        investigations = self.list_investigations(principal)
        restrictions = self._store.list_restrictions(tenant_id=principal.tenant_id)
        scoped = tuple(r for r in restrictions if principal.allows_case(r.case_id))
        active = tuple(r for r in scoped if r.blocks_financial_actions)
        open_count = sum(1 for i in investigations if i.status in {"OPEN", "UNDER_REVIEW"})
        awaiting = sum(1 for i in investigations if i.status == "AWAITING_EVIDENCE")
        return DashboardView(
            open_investigations=open_count,
            active_restrictions=len(active),
            awaiting_evidence=awaiting,
            aging_investigations=sum(1 for i in investigations if i.status != "CLOSED"),
            blocked_actions=len(active),
            investigations=investigations,
        )

    def record_finding(
        self,
        principal: Principal,
        investigation_id: str,
        request: RecordFindingRequest,
    ) -> Finding:
        investigation = self._require_investigation(investigation_id)
        self._authorize(
            principal,
            investigation.tenant_id,
            investigation.case_id,
            investigation.queue_ref,
        )
        try:
            classification = rules.assert_classification(request.classification)
            rules.assert_can_record_finding(investigation)
        except ValueError as exc:
            raise errors.ValidationError(str(exc)) from exc
        if (
            request.expected_revision is not None
            and investigation.revision != request.expected_revision
        ):
            raise errors.ConflictError("Investigation revision mismatch")

        now = rules.format_rfc3339(self._clock.now())
        finding = Finding(
            finding_id=_new_id("fnd"),
            investigation_id=investigation_id,
            classification=classification,
            evidence_ids=request.evidence_ids,
            notes=request.notes,
            recorded_by=principal.principal_id,
            recorded_at=now,
            revision=investigation.revision + 1,
        )
        self._store.save_finding(finding)
        updated = replace(
            investigation,
            status=rules.investigation_status_after_finding(classification),  # type: ignore[arg-type]
            finding_ids=(*investigation.finding_ids, finding.finding_id),
            evidence_ids=tuple(dict.fromkeys((*investigation.evidence_ids, *request.evidence_ids))),
            updated_at=now,
            revision=investigation.revision + 1,
        )
        self._store.save_investigation(updated)
        return finding

    def decide_restriction(
        self,
        principal: Principal,
        restriction_id: str,
        request: RestrictionDecisionRequest,
    ) -> RiskRestriction:
        restriction = self._require_restriction(restriction_id)
        investigation = self._require_investigation(restriction.investigation_id)
        self._authorize(
            principal,
            investigation.tenant_id,
            investigation.case_id,
            investigation.queue_ref,
        )
        try:
            decision = rules.assert_decision(request.decision)
            rules.assert_can_decide(
                restriction,
                investigation,
                expected_revision=request.expected_revision,
            )
        except ValueError as exc:
            message = str(exc)
            if "revision" in message.lower():
                raise errors.ConflictError(message) from exc
            raise errors.ValidationError(message) from exc
        if not request.reason.strip():
            raise errors.ValidationError("reason is required")

        now = rules.format_rfc3339(self._clock.now())
        updated = rules.apply_restriction_decision(
            restriction,
            decision=decision,
            actor_id=principal.principal_id,
            reason=request.reason,
            evidence_ids=request.evidence_ids,
            decided_at=now,
        )
        # Invariant: clearance never grants money authority.
        if updated.financial_approval_granted:
            raise errors.LedgerApprovalForbiddenError(
                "Risk restriction clearance must never grant financial approval"
            )

        # CLEAR: CAS-claim revision while block stays active, then emit resume,
        # then persist CLEARED. Concurrent CLEAR with the same expected_revision
        # conflicts before a second resume emit. Emit failure leaves the claim
        # (still blocking); retry with the claimed revision.
        if decision == "CLEAR":
            claim = replace(restriction, revision=restriction.revision + 1)
            self._store.compare_and_swap_restriction(
                claim, expected_revision=request.expected_revision
            )
            self._workflow.emit_resume(
                ResumeEvent(
                    event_type="risk.restriction.cleared",
                    investigation_id=investigation.investigation_id,
                    case_id=investigation.case_id,
                    restriction_id=restriction.restriction_id,
                    tenant_id=investigation.tenant_id,
                    financial_approval_granted=False,
                ),
                principal=principal,
            )
            cleared = replace(updated, revision=claim.revision)
            saved = self._store.compare_and_swap_restriction(
                cleared, expected_revision=claim.revision
            )
        else:
            saved = self._store.compare_and_swap_restriction(
                updated, expected_revision=request.expected_revision
            )
        inv_status = investigation.status
        if decision == "CLEAR":
            inv_status = "CLOSED"
        elif decision == "CONFIRM_FRAUD":
            inv_status = "CLOSED"
        self._store.save_investigation(
            replace(
                investigation,
                status=inv_status,  # type: ignore[arg-type]
                updated_at=now,
                revision=investigation.revision + 1,
            )
        )
        return saved

    def case_blocks_financial_actions(self, principal: Principal, case_id: str) -> bool:
        self._require_risk_officer(principal)
        if not principal.allows_case(case_id):
            raise errors.UnauthorizedError("Unauthorized or out of scope")
        restrictions = self._store.list_restrictions(tenant_id=principal.tenant_id, case_id=case_id)
        return rules.case_is_blocked(restrictions, case_id=case_id)

    def deny_ledger_approval(self, principal: Principal, *, action_id: str) -> None:
        """AUTH-21: this service never approves ledger actions for any caller."""
        del action_id, principal
        raise errors.LedgerApprovalForbiddenError(
            "Risk service cannot approve ledger refunds or financial actions"
        )

    def _require_investigation(self, investigation_id: str) -> Investigation:
        investigation = self._store.get_investigation(investigation_id)
        if investigation is None:
            raise errors.NotFoundError("Investigation not found")
        return investigation

    def _require_restriction(self, restriction_id: str) -> RiskRestriction:
        restriction = self._store.get_restriction(restriction_id)
        if restriction is None:
            raise errors.NotFoundError("Restriction not found")
        return restriction

    def _require_risk_officer(self, principal: Principal) -> None:
        if not principal.is_risk_officer():
            raise errors.UnauthorizedError("risk_officer role required")

    def _authorize(
        self,
        principal: Principal,
        tenant_id: str,
        case_id: str,
        queue_ref: str,
    ) -> None:
        self._require_risk_officer(principal)
        if (
            principal.tenant_id != tenant_id
            or not principal.allows_case(case_id)
            or not principal.allows_queue(queue_ref)
        ):
            raise errors.UnauthorizedError("Unauthorized or out of scope")
