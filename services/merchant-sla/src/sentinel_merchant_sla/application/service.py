"""Merchant SLA use cases: policies, tasks, overdue, follow-ups, escalate≠done."""

from __future__ import annotations

from sentinel_merchant_sla.application.errors import (
    ConflictError,
    ForbiddenError,
    NotFoundError,
    PeerMalformedError,
)
from sentinel_merchant_sla.application.ports import CaseApiPort, Clock, SlaStore
from sentinel_merchant_sla.contracts import (
    Principal,
    SlaInputError,
    SlaPolicy,
    SlaTarget,
    SlaTask,
    parse_create_task_body,
    parse_policy_body,
)
from sentinel_merchant_sla.domain.sla import (
    compute_due_at,
    compute_overdue,
    format_rfc3339,
    is_financially_resolved,
    parse_rfc3339,
    transition_assign,
    transition_complete,
    transition_escalate,
    validate_follow_up_at,
)


class MerchantSlaService:
    def __init__(self, *, store: SlaStore, clock: Clock, case_api: CaseApiPort) -> None:
        self._store = store
        self._clock = clock
        self._case_api = case_api

    def upsert_policy(self, principal: Principal, body: object) -> SlaPolicy:
        parsed = parse_policy_body(body)
        if parsed["tenant_id"] != principal.tenant_id:
            raise ForbiddenError("tenant scope denied")
        if not principal.allows_merchant(parsed["merchant_ref"]):
            raise ForbiddenError("merchant scope denied")
        policy_id = parsed["policy_id"] or self._store.next_id("sla-policy")
        policy = SlaPolicy(
            policy_id=policy_id,
            tenant_id=parsed["tenant_id"],
            merchant_ref=parsed["merchant_ref"],
            respond_within_seconds=parsed["respond_within_seconds"],
            resolve_within_seconds=parsed["resolve_within_seconds"],
        )
        return self._store.put_policy(policy)

    def get_policy(self, principal: Principal, policy_id: str) -> SlaPolicy:
        policy = self._store.get_policy(policy_id)
        if policy is None:
            raise NotFoundError("policy not found")
        self._assert_policy_scope(principal, policy)
        return policy

    def list_policies(self, principal: Principal, merchant_ref: str) -> list[SlaPolicy]:
        if not principal.allows_merchant(merchant_ref):
            raise ForbiddenError("merchant scope denied")
        return self._store.list_policies(tenant_id=principal.tenant_id, merchant_ref=merchant_ref)

    def create_task(self, principal: Principal, body: object) -> SlaTask:
        parsed = parse_create_task_body(body)
        if not principal.allows_case(parsed["case_id"]):
            raise ForbiddenError("case scope denied")
        policy = self._store.get_policy(parsed["policy_id"])
        if policy is None:
            raise NotFoundError("policy not found")
        self._assert_policy_scope(principal, policy)
        case = self._case_api.get_case(parsed["case_id"], principal)
        if case.tenant_id is not None and case.tenant_id != principal.tenant_id:
            raise ForbiddenError("case tenant scope denied")
        if case.merchant_ref is not None and case.merchant_ref != policy.merchant_ref:
            raise ForbiddenError("case merchant scope denied")
        if is_financially_resolved(case.status):
            raise ConflictError("case already financially resolved; SLA task not opened")
        opened_raw = case.opened_at or format_rfc3339(self._clock.now())
        opened_at = parse_rfc3339(opened_raw)
        target: SlaTarget = parsed["target"]
        due_at = compute_due_at(policy=policy, target=target, opened_at=opened_at)
        now = self._clock.now()
        status = "IN_PROGRESS" if parsed["assignee"] else "OPEN"
        task = SlaTask(
            task_id=self._store.next_id("sla-task"),
            case_id=case.case_id,
            assignee=parsed["assignee"],
            due_at=format_rfc3339(due_at),
            follow_up_at=None,
            overdue=compute_overdue(status=status, due_at=due_at, now=now),
            status=status,
            policy_id=policy.policy_id,
            tenant_id=policy.tenant_id,
            merchant_ref=policy.merchant_ref,
            case_status=case.status,
            financially_resolved=False,
        )
        return self._store.put_task(task)

    def get_task(self, principal: Principal, task_id: str) -> SlaTask:
        task = self._require_task(principal, task_id)
        return self._refresh_overdue(task)

    def list_tasks(
        self,
        principal: Principal,
        *,
        merchant_ref: str | None = None,
        case_id: str | None = None,
        overdue_only: bool = False,
    ) -> list[SlaTask]:
        if merchant_ref is not None and not principal.allows_merchant(merchant_ref):
            raise ForbiddenError("merchant scope denied")
        if case_id is not None and not principal.allows_case(case_id):
            raise ForbiddenError("case scope denied")
        tasks = [
            self._refresh_overdue(t)
            for t in self._store.list_tasks(
                tenant_id=principal.tenant_id,
                merchant_ref=merchant_ref,
                case_id=case_id,
            )
        ]
        if overdue_only:
            return [t for t in tasks if t.overdue]
        return tasks

    def assign_task(self, principal: Principal, task_id: str, body: object) -> SlaTask:
        assignee = body.get("assignee") if isinstance(body, dict) else None
        if not isinstance(assignee, str) or not assignee:
            raise SlaInputError("INVALID_INPUT", "assignee must be a nonempty string")

        task = self._require_task(principal, task_id)
        status = transition_assign(task.status)
        updated = self._replace(
            task,
            assignee=assignee,
            status=status,
        )
        return self._store.put_task(self._refresh_overdue(updated))

    def schedule_follow_up(self, principal: Principal, task_id: str, body: object) -> SlaTask:
        if not isinstance(body, dict) or not isinstance(body.get("follow_up_at"), str):
            raise SlaInputError("INVALID_INPUT", "follow_up_at must be a UTC RFC 3339 string")
        task = self._require_task(principal, task_id)
        if task.status == "DONE":
            raise ConflictError("cannot schedule follow-up on DONE task")
        follow_up = validate_follow_up_at(follow_up_at=body["follow_up_at"], now=self._clock.now())
        updated = self._replace(task, follow_up_at=format_rfc3339(follow_up))
        return self._store.put_task(self._refresh_overdue(updated))

    def escalate_task(self, principal: Principal, task_id: str, body: object) -> SlaTask:
        payload = body if isinstance(body, dict) else {}
        reason_code = str(payload.get("reason_code") or "SLA_BREACH")
        owner_queue = str(payload.get("owner_queue") or "merchant-ops")
        task = self._require_task(principal, task_id)
        new_status = transition_escalate(task.status)
        case = self._case_api.get_case(task.case_id, principal)
        escalated = self._case_api.escalate_case(
            task.case_id,
            expected_revision=case.revision,
            reason_code=reason_code,
            owner_queue=owner_queue,
            principal=principal,
        )
        if escalated.status == "VERIFIED_RESOLVED":
            raise PeerMalformedError(
                "escalation must not mark case VERIFIED_RESOLVED; peer rejected"
            )
        if escalated.status != "ESCALATED":
            raise PeerMalformedError(
                f"escalation expected case status ESCALATED, got {escalated.status}"
            )
        updated = self._replace(
            task,
            status=new_status,
            case_status=escalated.status,
            financially_resolved=is_financially_resolved(escalated.status),
        )
        # ESCALATED is unresolved work; overdue still applies.
        return self._store.put_task(self._refresh_overdue(updated))

    def complete_task(self, principal: Principal, task_id: str) -> SlaTask:
        task = self._require_task(principal, task_id)
        new_status = transition_complete(task.status)
        updated = self._replace(
            task,
            status=new_status,
            financially_resolved=False,
        )
        # Explicit non-financial DONE; does not set case VERIFIED_RESOLVED.
        return self._store.put_task(self._refresh_overdue(updated))

    def _require_task(self, principal: Principal, task_id: str) -> SlaTask:
        task = self._store.get_task(task_id)
        if task is None:
            raise NotFoundError("task not found")
        if task.tenant_id is not None and task.tenant_id != principal.tenant_id:
            raise ForbiddenError("tenant scope denied")
        if task.merchant_ref is not None and not principal.allows_merchant(task.merchant_ref):
            raise ForbiddenError("merchant scope denied")
        if not principal.allows_case(task.case_id):
            raise ForbiddenError("case scope denied")
        return task

    def _assert_policy_scope(self, principal: Principal, policy: SlaPolicy) -> None:
        if policy.tenant_id != principal.tenant_id:
            raise ForbiddenError("tenant scope denied")
        if not principal.allows_merchant(policy.merchant_ref):
            raise ForbiddenError("merchant scope denied")

    def _refresh_overdue(self, task: SlaTask) -> SlaTask:
        due_at = parse_rfc3339(task.due_at)
        overdue = compute_overdue(status=task.status, due_at=due_at, now=self._clock.now())
        if overdue == task.overdue:
            return task
        refreshed = self._replace(task, overdue=overdue)
        return self._store.put_task(refreshed)

    @staticmethod
    def _replace(task: SlaTask, **changes: object) -> SlaTask:
        data = {
            "task_id": task.task_id,
            "case_id": task.case_id,
            "assignee": task.assignee,
            "due_at": task.due_at,
            "follow_up_at": task.follow_up_at,
            "overdue": task.overdue,
            "status": task.status,
            "policy_id": task.policy_id,
            "tenant_id": task.tenant_id,
            "merchant_ref": task.merchant_ref,
            "case_status": task.case_status,
            "financially_resolved": task.financially_resolved,
        }
        data.update(changes)
        return SlaTask(**data)  # type: ignore[arg-type]
