"""Case API use cases."""

from __future__ import annotations

from datetime import UTC

from sentinel_api.application.authz import require_case_access, require_roles
from sentinel_api.application.ports import (
    CaseRepository,
    Clock,
    EvidencePort,
    IdGenerator,
    LedgerPort,
    VerifierPort,
    WorkflowPort,
)
from sentinel_api.domain.rules import (
    assert_verified_resolution,
    require_order_bound_to_principal,
    validate_case_create,
    validate_decision_request,
    validate_escalate,
    validate_message,
    validate_result,
)
from sentinel_api.domain.types import (
    Approval,
    Case,
    CaseCreated,
    CaseEvent,
    CaseInput,
    DomainError,
    EvidenceBundle,
    Principal,
    WorkflowRequest,
)


class CaseService:
    def __init__(
        self,
        *,
        repo: CaseRepository,
        clock: Clock,
        ids: IdGenerator,
        workflow: WorkflowPort,
        evidence: EvidencePort,
        ledger: LedgerPort,
        verifier: VerifierPort,
        service_authorization: str,
    ) -> None:
        self._repo = repo
        self._clock = clock
        self._ids = ids
        self._workflow = workflow
        self._evidence = evidence
        self._ledger = ledger
        self._verifier = verifier
        self._service_authorization = service_authorization

    def create_case(
        self, principal: Principal, body: dict, *, idempotency_key: str
    ) -> tuple[CaseCreated, int]:
        require_roles(principal, "customer", "operator")
        if not idempotency_key.strip():
            raise DomainError("INVALID_INPUT", "Idempotency-Key is required", 422)
        create = validate_case_create(body)
        require_order_bound_to_principal(
            create.order_reference,
            subject_refs=principal.subject_refs,
            enforce=principal.has_role("customer") or bool(principal.subject_refs),
        )
        case_id = self._ids.new_id("case")
        message_id = self._ids.new_id("msg")
        event_id = self._ids.new_id("evt")
        occurred = self._rfc3339()
        created, case, reused = self._repo.create_case(
            principal=principal,
            create=create,
            idempotency_key=idempotency_key,
            case_id=case_id,
            message_id=message_id,
            event_id=event_id,
            occurred_at=occurred,
        )
        if not reused:
            self._schedule_workflow(
                principal.tenant_id,
                case.case_id,
                case.revision,
                f"start:{case.case_id}:{case.revision}",
                "START",
            )
            self._flush_workflow()
        return created, 202

    def get_case(self, principal: Principal, case_id: str) -> Case:
        require_roles(principal, "customer", "operator", "supervisor", "workflow", "verifier")
        meta = self._require_meta(principal, case_id)
        require_case_access(
            principal,
            tenant_id=principal.tenant_id,
            case_id=case_id,
            subject_ref=str(meta["subject_ref"]),
        )
        case = self._repo.get_case(tenant_id=principal.tenant_id, case_id=case_id)
        if case is None:
            raise DomainError("NOT_FOUND", "Case not found", 404)
        return case

    def add_message(self, principal: Principal, case_id: str, body: dict) -> Case:
        require_roles(principal, "customer", "operator")
        message, language, expected = validate_message(body)
        meta = self._require_meta(principal, case_id)
        require_case_access(
            principal,
            tenant_id=principal.tenant_id,
            case_id=case_id,
            subject_ref=str(meta["subject_ref"]),
        )
        author = "OPERATOR" if principal.has_role("operator") else "CUSTOMER"
        case = self._repo.add_message(
            principal=principal,
            case_id=case_id,
            message=message,
            language=language,
            expected_revision=expected,
            message_id=self._ids.new_id("msg"),
            event_id=self._ids.new_id("evt"),
            author=author,
            occurred_at=self._rfc3339(),
        )
        self._schedule_workflow(
            principal.tenant_id,
            case.case_id,
            case.revision,
            f"input:{case.case_id}:{case.revision}",
            "INPUT",
        )
        self._flush_workflow()
        return case

    def list_events(self, principal: Principal, case_id: str, *, after: int) -> list[CaseEvent]:
        require_roles(principal, "customer", "operator", "supervisor")
        meta = self._require_meta(principal, case_id)
        require_case_access(
            principal,
            tenant_id=principal.tenant_id,
            case_id=case_id,
            subject_ref=str(meta["subject_ref"]),
        )
        if after < 0:
            raise DomainError("INVALID_INPUT", "after must be >= 0", 422)
        return self._repo.list_events(
            tenant_id=principal.tenant_id, case_id=case_id, after_sequence=after
        )

    def list_queue(
        self, principal: Principal, *, status: str | None, after: str | None
    ) -> tuple[list[Case], str | None]:
        require_roles(principal, "operator", "supervisor")
        return self._repo.list_queue(
            tenant_id=principal.tenant_id, status=status, after=after, limit=50
        )

    def get_ops_evidence(
        self, principal: Principal, case_id: str, *, authorization: str
    ) -> EvidenceBundle:
        require_roles(principal, "operator", "supervisor")
        meta = self._require_meta(principal, case_id)
        require_case_access(
            principal,
            tenant_id=principal.tenant_id,
            case_id=case_id,
            subject_ref=str(meta["subject_ref"]),
        )
        return self._evidence.get_case_evidence(case_id, authorization=authorization)

    def decide(
        self,
        principal: Principal,
        action_id: str,
        body: dict,
        *,
        authorization: str,
    ) -> Approval:
        require_roles(principal, "supervisor")
        request = validate_decision_request(body)
        find = getattr(self._repo, "find_case_for_action", None)
        case_id = (
            find(tenant_id=principal.tenant_id, action_id=action_id) if callable(find) else None
        )
        if not case_id:
            raise DomainError("NOT_FOUND", "Action not bound to a case", 404)
        meta = self._require_meta(principal, case_id)
        require_case_access(
            principal,
            tenant_id=principal.tenant_id,
            case_id=case_id,
            subject_ref=str(meta["subject_ref"]),
        )
        # Forward the original authenticated supervisor token; never elevate.
        approval = self._ledger.decide(action_id, request, authorization=authorization)
        self._schedule_workflow(
            principal.tenant_id,
            case_id,
            request.case_revision,
            f"decision:{action_id}:{request.action_digest}:{request.case_revision}",
            "DECISION",
        )
        self._flush_workflow()
        return approval

    def escalate(self, principal: Principal, case_id: str, body: dict) -> Case:
        require_roles(principal, "operator", "supervisor")
        expected, reason, queue = validate_escalate(body)
        meta = self._require_meta(principal, case_id)
        require_case_access(
            principal,
            tenant_id=principal.tenant_id,
            case_id=case_id,
            subject_ref=str(meta["subject_ref"]),
        )
        return self._repo.escalate(
            principal=principal,
            case_id=case_id,
            expected_revision=expected,
            reason_code=reason,
            owner_queue=queue,
            event_id=self._ids.new_id("evt"),
            occurred_at=self._rfc3339(),
        )

    def get_input(self, principal: Principal, case_id: str, revision: int) -> CaseInput:
        require_roles(principal, "workflow")
        if revision < 1:
            raise DomainError("INVALID_INPUT", "revision must be positive", 422)
        meta = self._require_meta(principal, case_id)
        require_case_access(
            principal,
            tenant_id=principal.tenant_id,
            case_id=case_id,
            subject_ref=str(meta["subject_ref"]),
        )
        snapshot = self._repo.get_input(
            tenant_id=principal.tenant_id, case_id=case_id, revision=revision
        )
        if snapshot is None:
            raise DomainError("NOT_FOUND", "Case input revision not found", 404)
        return snapshot

    def apply_result(self, principal: Principal, case_id: str, body: dict) -> Case:
        require_roles(principal, "workflow", "verifier")
        result = validate_result(body)
        meta = self._require_meta(principal, case_id)
        require_case_access(
            principal,
            tenant_id=principal.tenant_id,
            case_id=case_id,
            subject_ref=str(meta["subject_ref"]),
        )
        assessment_ref = None
        if result.status == "VERIFIED_RESOLVED":
            assert result.assessment_id is not None
            assessment = self._verifier.get_assessment(
                result.assessment_id, authorization=self._service_authorization
            )
            assert_verified_resolution(
                result=result,
                case_id=case_id,
                assessment=assessment,
                now=self._clock.now().astimezone(UTC),
            )
            assessment_ref = assessment.assessment_id
        return self._repo.apply_result(
            principal=principal,
            case_id=case_id,
            result=result,
            event_id=self._ids.new_id("evt"),
            occurred_at=self._rfc3339(),
            assessment_ref=assessment_ref,
        )

    def _require_meta(self, principal: Principal, case_id: str) -> dict:
        meta = self._repo.get_case_meta(tenant_id=principal.tenant_id, case_id=case_id)
        if meta is None:
            raise DomainError("NOT_FOUND", "Case not found", 404)
        return meta

    def _rfc3339(self) -> str:
        return self._clock.now().astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    def _schedule_workflow(
        self,
        tenant_id: str,
        case_id: str,
        revision: int,
        job_key: str,
        event: str,
    ) -> None:
        request = WorkflowRequest(
            case_id=case_id,
            case_revision=revision,
            job_key=job_key,
            event=event,  # type: ignore[arg-type]
        )
        self._repo.enqueue_workflow(tenant_id=tenant_id, request=request)

    def _flush_workflow(self) -> None:
        for row_id, request in self._repo.claim_workflow_jobs():
            try:
                self._workflow.start_run(request, authorization=self._service_authorization)
                self._repo.mark_workflow_job(job_row_id=row_id, status="DELIVERED")
            except DomainError as exc:
                if exc.http_status == 503:
                    self._repo.mark_workflow_job(
                        job_row_id=row_id, status="PENDING", detail=exc.code
                    )
                else:
                    self._repo.mark_workflow_job(
                        job_row_id=row_id, status="FAILED", detail=exc.code
                    )
