"""LangGraph state schema."""

from __future__ import annotations

from typing import Any, TypedDict


class WorkflowState(TypedDict, total=False):
    tenant_id: str
    case_id: str
    case_revision: int
    event: str
    job_id: str
    job_key: str
    thread_id: str
    status: str
    reason_code: str
    investigation_steps: int
    investigation_budget: int
    model_retries: int
    model_retry_budget: int
    case: dict[str, Any]
    case_input: dict[str, Any]
    evidence: list[dict[str, Any]]
    evidence_ids: list[str]
    model_result: dict[str, Any]
    proposal: dict[str, Any]
    policy_result: dict[str, Any]
    action_digest: str
    approval: dict[str, Any]
    action_id: str
    provider_ref: str
    assessment_id: str
    operation_key: str
    terminal: bool
    pending_result: dict[str, Any]
    error: str
