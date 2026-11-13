"""Accept runs, execute durable graph, flush case-result outbox."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from langgraph.types import Command

from sentinel_workflow.application.errors import (
    PeerError,
    PeerUnavailableError,
    UnauthorizedError,
    ValidationError,
    WorkflowError,
)
from sentinel_workflow.application.ports import (
    CaseApiPort,
    DecisionStorePort,
    JobStorePort,
    OutboxPort,
)
from sentinel_workflow.domain.types import Ack, Approval, CaseResult, Principal, WorkflowRequest
from sentinel_workflow.graph.context import CONFIG_KEY, GraphDeps

logger = logging.getLogger(__name__)


@dataclass
class WorkflowService:
    jobs: JobStorePort
    outbox: OutboxPort
    decisions: DecisionStorePort
    case_api: CaseApiPort
    graph: Any
    deps: GraphDeps
    investigation_budget: int = 8
    model_retry_budget: int = 2

    def accept(
        self,
        request: WorkflowRequest,
        principal: Principal,
        *,
        run_now: bool = True,
        resume_approval: Approval | None = None,
    ) -> Ack:
        if request.event not in {"START", "INPUT", "DECISION", "RECHECK"}:
            raise ValidationError("Unsupported workflow event")
        thread_id = f"{principal.tenant_id}:{request.case_id}:{request.case_revision}"
        payload = request.model_dump(exclude_none=True)
        job_id, created = self.jobs.accept_job(
            tenant_id=principal.tenant_id,
            job_key=request.job_key,
            payload=payload,
            thread_id=thread_id,
        )
        if resume_approval is not None:
            self.decisions.put_decision(thread_id, resume_approval, principal.principal_id)

        if created and run_now:
            self.execute(
                request=request,
                principal=principal,
                job_id=job_id,
                thread_id=thread_id,
                resume_approval=resume_approval,
            )
        return Ack(job_id=job_id)

    def execute(
        self,
        *,
        request: WorkflowRequest,
        principal: Principal,
        job_id: str,
        thread_id: str,
        resume_approval: Approval | None = None,
    ) -> None:
        config = {
            "configurable": {
                "thread_id": thread_id,
                CONFIG_KEY: self.deps,
            }
        }
        decision = resume_approval
        if decision is None and request.event == "DECISION":
            stored = self.decisions.get_decision(thread_id)
            if stored is not None:
                decision = Approval.model_validate(stored["approval"])
            else:
                decision = self._approval_from_ledger(thread_id)

        try:
            if request.event in {"DECISION", "RECHECK", "INPUT"} and self._has_checkpoint(
                thread_id
            ):
                resume_value: dict[str, Any]
                if request.event == "DECISION":
                    if decision is None:
                        raise ValidationError("Missing approval for DECISION resume")
                    resume_value = decision.model_dump(exclude_none=True)
                elif request.event == "RECHECK":
                    resume_value = {"event": "RECHECK"}
                else:
                    resume_value = {"event": "INPUT"}
                self.graph.invoke(Command(resume=resume_value), config)
            else:
                initial = {
                    "tenant_id": principal.tenant_id,
                    "case_id": request.case_id,
                    "case_revision": request.case_revision,
                    "event": request.event,
                    "job_id": job_id,
                    "job_key": request.job_key,
                    "thread_id": thread_id,
                    "investigation_steps": 0,
                    "investigation_budget": self.investigation_budget,
                    "model_retries": 0,
                    "model_retry_budget": self.model_retry_budget,
                    "terminal": False,
                }
                self.graph.invoke(initial, config)
            self.jobs.mark_job_status(job_id, "completed")
        except Exception as exc:
            logger.exception("workflow run failed job_id=%s", job_id)
            self.jobs.mark_job_status(job_id, "failed", detail=str(exc))
            raise
        finally:
            self.flush_outbox()

    def flush_outbox(self) -> int:
        delivered = 0
        for item in self.outbox.pending():
            payload = CaseResult.model_validate(item["payload"])
            try:
                self._submit_result_reconciled(item["case_id"], payload)
                self.outbox.mark_delivered(item["outbox_id"])
                delivered += 1
            except PeerUnavailableError as exc:
                self.outbox.mark_retry(item["outbox_id"], exc.message)
            except PeerError as exc:
                if exc.status_code == 409:
                    # Identical event already applied, or unrecoverable conflict after reconcile.
                    self.outbox.mark_delivered(item["outbox_id"])
                    delivered += 1
                else:
                    self.outbox.mark_retry(item["outbox_id"], exc.message)
            except WorkflowError as exc:
                self.outbox.mark_retry(item["outbox_id"], exc.message)
        return delivered

    def _submit_result_reconciled(self, case_id: str, payload: CaseResult) -> None:
        try:
            self.case_api.submit_result(case_id, payload)
            return
        except PeerError as exc:
            if exc.status_code != 409:
                raise
        # Stale revision: read current case and retry once with reconciled revision.
        case = self.case_api.get_case(case_id)
        reconciled = payload.model_copy(update={"expected_revision": case.revision})
        self.case_api.submit_result(case_id, reconciled)

    def _has_checkpoint(self, thread_id: str) -> bool:
        try:
            config = {"configurable": {"thread_id": thread_id}}
            state = self.graph.get_state(config)
            return bool(state and state.values)
        except Exception:
            return False

    def _approval_from_ledger(self, thread_id: str) -> Approval | None:
        config = {"configurable": {"thread_id": thread_id, CONFIG_KEY: self.deps}}
        try:
            state = self.graph.get_state(config)
        except Exception:
            return None
        action_id = (state.values or {}).get("action_id")
        if not action_id:
            tasks = getattr(state, "tasks", ()) or ()
            for task in tasks:
                interrupts = getattr(task, "interrupts", ()) or ()
                for item in interrupts:
                    value = getattr(item, "value", None) or {}
                    action_id = value.get("action_id")
                    if action_id:
                        break
        if not action_id:
            return None
        record = self.deps.ledger.get_action(action_id)
        if record.approval is None:
            return None
        return record.approval


def authorize_run(principal: Principal, case_id: str) -> None:
    roles = set(principal.roles)
    if not roles.intersection({"workflow", "verifier"}):
        raise UnauthorizedError("Role cannot invoke workflow runs")
    if case_id not in principal.case_ids and "*" not in principal.case_ids:
        raise UnauthorizedError("Case out of scope")
