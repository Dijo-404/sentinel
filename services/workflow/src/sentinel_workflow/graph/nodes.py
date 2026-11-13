"""Specialist graph nodes. Models propose; ledger/policy own money and approval."""

from __future__ import annotations

from typing import Any, Literal

from langchain_core.runnables import RunnableConfig
from langgraph.types import interrupt

from sentinel_workflow.application.errors import PeerError, PeerUnavailableError, WorkflowError
from sentinel_workflow.domain.digest import action_digest
from sentinel_workflow.domain.types import (
    Case,
    CaseInput,
    CaseResult,
    Evidence,
    ModelRequest,
    PolicyRequest,
    ProposalRequest,
    RefundAction,
    ReservationRequest,
    VerificationRequest,
)
from sentinel_workflow.graph.context import deps_from_config
from sentinel_workflow.graph.state import WorkflowState


def _route_after_plan(state: WorkflowState) -> Literal["policy", "clarify", "escalate", "budget"]:
    if state.get("terminal"):
        status = state.get("status")
        if status == "NEEDS_INPUT":
            return "clarify"
        return "escalate"
    steps = int(state.get("investigation_steps") or 0)
    budget = state.get("investigation_budget")
    if budget is None:
        budget = 8
    if steps > int(budget):
        return "budget"
    return "policy"


def _route_after_policy(
    state: WorkflowState,
) -> Literal["approval", "execute", "clarify", "escalate"]:
    outcome = (state.get("policy_result") or {}).get("outcome")
    if outcome == "REQUIRE_APPROVAL":
        return "approval"
    if outcome == "ALLOW":
        return "execute"
    if outcome == "NEED_EVIDENCE":
        return "clarify"
    return "escalate"


def _route_after_verify(
    state: WorkflowState,
) -> Literal["wait", "resolved", "escalate"]:
    status = state.get("status")
    if status == "WAITING_EXTERNAL":
        return "wait"
    if status == "VERIFIED_RESOLVED":
        return "resolved"
    return "escalate"


def load_input(state: WorkflowState, config: RunnableConfig) -> dict[str, Any]:
    deps = deps_from_config(config)
    case_input = deps.case_api.get_input(state["case_id"], state["case_revision"])
    case = deps.case_api.get_case(state["case_id"])
    return {
        "case_input": case_input.model_dump(exclude_none=True),
        "case": case.model_dump(exclude_none=True),
        "status": "INVESTIGATING",
        "reason_code": "INVESTIGATION_STARTED",
        "investigation_steps": int(state.get("investigation_steps") or 0) + 1,
    }


def collect_evidence(state: WorkflowState, config: RunnableConfig) -> dict[str, Any]:
    deps = deps_from_config(config)
    order_reference = (state.get("case_input") or {}).get("order_reference") or ""
    try:
        bundle = deps.evidence.collect(state["case_id"], state["case_revision"], order_reference)
    except PeerUnavailableError:
        return {
            "status": "ESCALATED",
            "reason_code": "EVIDENCE_UNAVAILABLE",
            "terminal": True,
            "pending_result": _pending(
                state,
                status="ESCALATED",
                reason_code="EVIDENCE_UNAVAILABLE",
                evidence_ids=[],
            ),
        }
    except PeerError as exc:
        if exc.code in {"UNAUTHORIZED", "FORBIDDEN", "OUT_OF_SCOPE"}:
            return {
                "status": "ESCALATED",
                "reason_code": "EVIDENCE_UNAUTHORIZED",
                "terminal": True,
                "pending_result": _pending(
                    state,
                    status="ESCALATED",
                    reason_code="EVIDENCE_UNAUTHORIZED",
                    evidence_ids=[],
                ),
            }
        return {
            "status": "ESCALATED",
            "reason_code": "EVIDENCE_MALFORMED",
            "terminal": True,
            "pending_result": _pending(
                state,
                status="ESCALATED",
                reason_code="EVIDENCE_MALFORMED",
                evidence_ids=[],
            ),
        }

    evidence = [e.model_dump(exclude_none=True) for e in bundle.evidence]
    if not evidence or "MISSING_EVIDENCE" in bundle.reconciliation_codes:
        return {
            "evidence": evidence,
            "evidence_ids": [e["evidence_id"] for e in evidence],
            "status": "NEEDS_INPUT",
            "reason_code": "MISSING_EVIDENCE",
            "terminal": True,
            "pending_result": _pending(
                state,
                status="NEEDS_INPUT",
                reason_code="MISSING_EVIDENCE",
                evidence_ids=[e["evidence_id"] for e in evidence],
            ),
        }
    return {
        "evidence": evidence,
        "evidence_ids": [e["evidence_id"] for e in evidence],
        "status": "RECONCILING",
        "reason_code": "EVIDENCE_COLLECTED",
        "terminal": False,
    }


def plan(state: WorkflowState, config: RunnableConfig) -> dict[str, Any]:
    deps = deps_from_config(config)
    case = Case.model_validate(state["case"])
    case_input = CaseInput.model_validate(state["case_input"])
    evidence = [Evidence.model_validate(e) for e in state.get("evidence") or []]
    request = ModelRequest(case=case, input=case_input, evidence=evidence)
    retries = int(state.get("model_retries") or 0)
    budget = int(state.get("model_retry_budget") or 2)
    try:
        result = deps.model.propose(request)
    except PeerUnavailableError:
        if retries + 1 > budget:
            return {
                "model_retries": retries + 1,
                "status": "ESCALATED",
                "reason_code": "MODEL_OUTAGE_EXHAUSTED",
                "terminal": True,
                "pending_result": _pending(
                    state,
                    status="ESCALATED",
                    reason_code="MODEL_OUTAGE_EXHAUSTED",
                    evidence_ids=state.get("evidence_ids") or [],
                ),
            }
        return {
            "model_retries": retries + 1,
            "status": "ESCALATED",
            "reason_code": "MODEL_OUTAGE",
            "terminal": True,
            "pending_result": _pending(
                state,
                status="ESCALATED",
                reason_code="MODEL_OUTAGE",
                evidence_ids=state.get("evidence_ids") or [],
            ),
        }
    except (PeerError, WorkflowError, ValueError):
        if retries + 1 > budget:
            return {
                "model_retries": retries + 1,
                "status": "ESCALATED",
                "reason_code": "MODEL_MALFORMED_EXHAUSTED",
                "terminal": True,
                "pending_result": _pending(
                    state,
                    status="ESCALATED",
                    reason_code="MODEL_MALFORMED_EXHAUSTED",
                    evidence_ids=state.get("evidence_ids") or [],
                ),
            }
        return {
            "model_retries": retries + 1,
            "status": "ESCALATED",
            "reason_code": "MODEL_MALFORMED",
            "terminal": True,
            "pending_result": _pending(
                state,
                status="ESCALATED",
                reason_code="MODEL_MALFORMED",
                evidence_ids=state.get("evidence_ids") or [],
            ),
        }

    payload = result.model_dump(exclude_none=True)
    if result.outcome == "NEEDS_INPUT":
        return {
            "model_result": payload,
            "status": "NEEDS_INPUT",
            "reason_code": (result.reason_codes or ["MODEL_NEEDS_INPUT"])[0],
            "terminal": True,
            "pending_result": _pending(
                state,
                status="NEEDS_INPUT",
                reason_code=(result.reason_codes or ["MODEL_NEEDS_INPUT"])[0],
                evidence_ids=state.get("evidence_ids") or [],
            ),
        }
    if result.outcome == "ESCALATE" or result.proposal is None:
        return {
            "model_result": payload,
            "status": "ESCALATED",
            "reason_code": (result.reason_codes or ["MODEL_ESCALATE"])[0],
            "terminal": True,
            "pending_result": _pending(
                state,
                status="ESCALATED",
                reason_code=(result.reason_codes or ["MODEL_ESCALATE"])[0],
                evidence_ids=state.get("evidence_ids") or [],
            ),
        }

    proposal = dict(result.proposal)
    proposal.setdefault("case_id", state["case_id"])
    proposal.setdefault("case_revision", state["case_revision"])
    proposal.setdefault("evidence_ids", state.get("evidence_ids") or [])
    proposal.setdefault("policy_version", deps.policy_version)
    digest = action_digest(proposal)
    operation_key = f"{state['case_id']}:{digest}"
    return {
        "model_result": payload,
        "proposal": proposal,
        "action_digest": digest,
        "operation_key": operation_key,
        "status": "PLANNING",
        "reason_code": "PROPOSAL_READY",
        "terminal": False,
    }


def budget_exhausted(state: WorkflowState, config: RunnableConfig) -> dict[str, Any]:
    del config
    return {
        "status": "ESCALATED",
        "reason_code": "INVESTIGATION_BUDGET_EXHAUSTED",
        "terminal": True,
        "pending_result": _pending(
            state,
            status="ESCALATED",
            reason_code="INVESTIGATION_BUDGET_EXHAUSTED",
            evidence_ids=state.get("evidence_ids") or [],
        ),
    }


def policy_check(state: WorkflowState, config: RunnableConfig) -> dict[str, Any]:
    deps = deps_from_config(config)
    from sentinel_workflow.domain.types import Approval as ApprovalModel

    evidence = [Evidence.model_validate(e) for e in state.get("evidence") or []]
    raw_approval = state.get("approval")
    approval = ApprovalModel.model_validate(raw_approval) if raw_approval else None
    request = PolicyRequest(
        payload=state["proposal"],
        evidence=evidence,
        approval=approval,
    )
    try:
        result = deps.policy.evaluate(request)
    except (PeerUnavailableError, PeerError):
        return {
            "status": "ESCALATED",
            "reason_code": "POLICY_PEER_FAILURE",
            "terminal": True,
            "pending_result": _pending(
                state,
                status="ESCALATED",
                reason_code="POLICY_PEER_FAILURE",
                evidence_ids=state.get("evidence_ids") or [],
            ),
        }
    payload = result.model_dump(exclude_none=True)
    if result.outcome == "DENY":
        return {
            "policy_result": payload,
            "status": "ESCALATED",
            "reason_code": (result.reason_codes or ["POLICY_DENY"])[0],
            "terminal": True,
            "pending_result": _pending(
                state,
                status="ESCALATED",
                reason_code=(result.reason_codes or ["POLICY_DENY"])[0],
                evidence_ids=state.get("evidence_ids") or [],
            ),
        }
    if result.outcome == "NEED_EVIDENCE":
        return {
            "policy_result": payload,
            "status": "NEEDS_INPUT",
            "reason_code": (result.reason_codes or ["NEED_EVIDENCE"])[0],
            "terminal": True,
            "pending_result": _pending(
                state,
                status="NEEDS_INPUT",
                reason_code=(result.reason_codes or ["NEED_EVIDENCE"])[0],
                evidence_ids=state.get("evidence_ids") or [],
            ),
        }
    return {
        "policy_result": payload,
        "action_digest": result.action_digest or state.get("action_digest"),
        "status": "POLICY_CHECK",
        "reason_code": "POLICY_EVALUATED",
        "terminal": False,
    }


def approval_gate(state: WorkflowState, config: RunnableConfig) -> dict[str, Any]:
    """Idempotent proposal, then interrupt. Reservation happens only after authenticated resume."""
    deps = deps_from_config(config)
    proposal = RefundAction.model_validate(state["proposal"])
    digest = state.get("action_digest") or action_digest(proposal.model_dump(exclude_none=True))
    operation_key = state.get("operation_key") or f"{state['case_id']}:{digest}"
    action_id = state.get("action_id")
    provider_ref = state.get("provider_ref")
    if not action_id:
        try:
            record = deps.ledger.create_proposal(
                ProposalRequest(
                    operation_key=operation_key,
                    payload=proposal,
                    action_digest=digest,
                )
            )
            action_id = record.action_id
            provider_ref = record.provider_ref
        except (PeerUnavailableError, PeerError):
            return {
                "status": "ESCALATED",
                "reason_code": "LEDGER_PEER_FAILURE",
                "terminal": True,
                "pending_result": _pending(
                    state,
                    status="ESCALATED",
                    reason_code="LEDGER_PEER_FAILURE",
                    evidence_ids=state.get("evidence_ids") or [],
                ),
            }

    pending = _pending(
        state,
        status="WAITING_APPROVAL",
        reason_code="SUPERVISOR_REQUIRED",
        evidence_ids=state.get("evidence_ids") or [],
        action_id=action_id,
    )
    deps.outbox.enqueue_result(
        tenant_id=state["tenant_id"],
        case_id=state["case_id"],
        event_key=pending["event_key"],
        payload=pending,
    )
    decision = interrupt(
        {
            "type": "WAITING_APPROVAL",
            "case_id": state["case_id"],
            "case_revision": state["case_revision"],
            "action_id": action_id,
            "action_digest": digest,
            "operation_key": operation_key,
        }
    )
    if not isinstance(decision, dict):
        return {
            "action_id": action_id,
            "provider_ref": provider_ref,
            "operation_key": operation_key,
            "action_digest": digest,
            "status": "ESCALATED",
            "reason_code": "INVALID_APPROVAL_RESUME",
            "terminal": True,
            "pending_result": _pending(
                state,
                status="ESCALATED",
                reason_code="INVALID_APPROVAL_RESUME",
                evidence_ids=state.get("evidence_ids") or [],
                action_id=action_id,
            ),
        }
    if decision.get("decision") == "REJECT":
        return {
            "action_id": action_id,
            "provider_ref": provider_ref,
            "operation_key": operation_key,
            "action_digest": digest,
            "approval": decision,
            "status": "ESCALATED",
            "reason_code": "APPROVAL_REJECTED",
            "terminal": True,
            "pending_result": _pending(
                state,
                status="ESCALATED",
                reason_code="APPROVAL_REJECTED",
                evidence_ids=state.get("evidence_ids") or [],
                action_id=action_id,
            ),
        }
    return {
        "action_id": action_id,
        "provider_ref": provider_ref,
        "operation_key": operation_key,
        "action_digest": digest,
        "approval": decision,
        "status": "POLICY_CHECK",
        "reason_code": "APPROVAL_RECEIVED",
        "terminal": False,
    }


def execute_ledger(state: WorkflowState, config: RunnableConfig) -> dict[str, Any]:
    """Reserve (or propose+reserve) with stable operation_key — safe under node replay."""
    deps = deps_from_config(config)
    proposal = RefundAction.model_validate(state["proposal"])
    digest = state.get("action_digest") or action_digest(proposal.model_dump(exclude_none=True))
    operation_key = state.get("operation_key") or f"{state['case_id']}:{digest}"
    approval = state.get("approval")
    try:
        record_action_id = state.get("action_id")
        provider_ref = state.get("provider_ref")
        if not record_action_id:
            record = deps.ledger.create_proposal(
                ProposalRequest(
                    operation_key=operation_key,
                    payload=proposal,
                    action_digest=digest,
                )
            )
            record_action_id = record.action_id
            provider_ref = record.provider_ref
        if approval and approval.get("decision") == "APPROVE":
            record = deps.ledger.reserve(
                ReservationRequest(
                    operation_key=operation_key,
                    payload=proposal,
                    action_digest=digest,
                    approval_id=approval["approval_id"],
                )
            )
            record_action_id = record.action_id
            provider_ref = record.provider_ref
        elif not approval:
            # Refunds always require approval per contract; escalate if policy ALLOW without one.
            return {
                "action_id": record_action_id,
                "provider_ref": provider_ref,
                "operation_key": operation_key,
                "action_digest": digest,
                "status": "ESCALATED",
                "reason_code": "APPROVAL_REQUIRED",
                "terminal": True,
                "pending_result": _pending(
                    state,
                    status="ESCALATED",
                    reason_code="APPROVAL_REQUIRED",
                    evidence_ids=state.get("evidence_ids") or [],
                    action_id=record_action_id,
                ),
            }
    except (PeerUnavailableError, PeerError) as exc:
        return {
            "status": "ESCALATED",
            "reason_code": "LEDGER_PEER_FAILURE",
            "error": exc.message,
            "terminal": True,
            "pending_result": _pending(
                state,
                status="ESCALATED",
                reason_code="LEDGER_PEER_FAILURE",
                evidence_ids=state.get("evidence_ids") or [],
            ),
        }
    return {
        "action_id": record_action_id,
        "provider_ref": provider_ref,
        "operation_key": operation_key,
        "action_digest": digest,
        "status": "EXECUTING",
        "reason_code": "ACTION_RESERVED",
        "terminal": False,
    }


def verify(state: WorkflowState, config: RunnableConfig) -> dict[str, Any]:
    deps = deps_from_config(config)
    action_id = state.get("action_id")
    provider_ref = state.get("provider_ref")
    if not action_id or not provider_ref:
        return {
            "status": "ESCALATED",
            "reason_code": "MISSING_ACTION_REF",
            "terminal": True,
            "pending_result": _pending(
                state,
                status="ESCALATED",
                reason_code="MISSING_ACTION_REF",
                evidence_ids=state.get("evidence_ids") or [],
            ),
        }
    request = VerificationRequest(
        case_id=state["case_id"],
        case_revision=state["case_revision"],
        action_id=action_id,
        provider_ref=provider_ref,
    )
    idem = f"recheck:{operation_key_or(state)}:{action_id}"
    try:
        deps.verifier.schedule_recheck(request, idem)
        assessment = deps.verifier.assess(request)
    except (PeerUnavailableError, PeerError):
        return {
            "status": "ESCALATED",
            "reason_code": "VERIFIER_PEER_FAILURE",
            "terminal": True,
            "pending_result": _pending(
                state,
                status="ESCALATED",
                reason_code="VERIFIER_PEER_FAILURE",
                evidence_ids=state.get("evidence_ids") or [],
                action_id=action_id,
            ),
        }
    if assessment.status == "WAITING":
        pending = _pending(
            state,
            status="WAITING_EXTERNAL",
            reason_code=(assessment.reason_codes or ["PENDING_PROVIDER"])[0],
            evidence_ids=state.get("evidence_ids") or [],
            action_id=action_id,
            assessment_id=assessment.assessment_id,
        )
        return {
            "assessment_id": assessment.assessment_id,
            "status": "WAITING_EXTERNAL",
            "reason_code": pending["reason_code"],
            "terminal": True,
            "pending_result": pending,
        }
    if assessment.status == "VERIFIED":
        pending = _pending(
            state,
            status="VERIFIED_RESOLVED",
            reason_code=(assessment.reason_codes or ["CREDIT_CONFIRMED"])[0],
            evidence_ids=state.get("evidence_ids") or [],
            action_id=action_id,
            assessment_id=assessment.assessment_id,
        )
        return {
            "assessment_id": assessment.assessment_id,
            "status": "VERIFIED_RESOLVED",
            "reason_code": pending["reason_code"],
            "terminal": True,
            "pending_result": pending,
        }
    pending = _pending(
        state,
        status="ESCALATED",
        reason_code=(assessment.reason_codes or ["VERIFICATION_CONFLICT"])[0],
        evidence_ids=state.get("evidence_ids") or [],
        action_id=action_id,
        assessment_id=assessment.assessment_id,
    )
    return {
        "assessment_id": assessment.assessment_id,
        "status": "ESCALATED",
        "reason_code": pending["reason_code"],
        "terminal": True,
        "pending_result": pending,
    }


def deliver(state: WorkflowState, config: RunnableConfig) -> dict[str, Any]:
    deps = deps_from_config(config)
    pending = state.get("pending_result")
    if pending is None:
        pending = _pending(
            state,
            status=state.get("status") or "ESCALATED",
            reason_code=state.get("reason_code") or "UNKNOWN",
            evidence_ids=state.get("evidence_ids") or [],
            action_id=state.get("action_id"),
            assessment_id=state.get("assessment_id"),
        )
    deps.outbox.enqueue_result(
        tenant_id=state["tenant_id"],
        case_id=state["case_id"],
        event_key=pending["event_key"],
        payload=pending,
    )
    return {"pending_result": pending, "terminal": True}


def wait_external(state: WorkflowState, config: RunnableConfig) -> dict[str, Any]:
    """Durable wait for RECHECK; interrupt so restart preserves WAITING_EXTERNAL."""
    deps = deps_from_config(config)
    pending = state.get("pending_result") or _pending(
        state,
        status="WAITING_EXTERNAL",
        reason_code=state.get("reason_code") or "PENDING_PROVIDER",
        evidence_ids=state.get("evidence_ids") or [],
        action_id=state.get("action_id"),
        assessment_id=state.get("assessment_id"),
    )
    deps.outbox.enqueue_result(
        tenant_id=state["tenant_id"],
        case_id=state["case_id"],
        event_key=pending["event_key"],
        payload=pending,
    )
    resume = interrupt(
        {
            "type": "WAITING_EXTERNAL",
            "case_id": state["case_id"],
            "action_id": state.get("action_id"),
        }
    )
    if isinstance(resume, dict) and resume.get("event") == "RECHECK":
        return {
            "status": "VERIFYING",
            "reason_code": "RECHECK_REQUESTED",
            "terminal": False,
            "event": "RECHECK",
        }
    return {"terminal": True, "pending_result": pending}


def operation_key_or(state: WorkflowState) -> str:
    digest = state.get("action_digest") or "none"
    return state.get("operation_key") or f"{state['case_id']}:{digest}"


def _pending(
    state: WorkflowState,
    *,
    status: str,
    reason_code: str,
    evidence_ids: list[str],
    action_id: str | None = None,
    assessment_id: str | None = None,
) -> dict[str, Any]:
    event_key = f"result:{state['job_key']}:{status}:{reason_code}"
    body: dict[str, Any] = {
        "event_key": event_key,
        "expected_revision": state["case_revision"],
        "status": status,
        "evidence_ids": evidence_ids,
        "reason_code": reason_code,
    }
    if action_id:
        body["action_id"] = action_id
    if assessment_id:
        body["assessment_id"] = assessment_id
    # Validate shape early.
    CaseResult.model_validate(body)
    return body
