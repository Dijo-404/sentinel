"""Gateway output validates against the callers' pinned wire rules.

Pinned from main @ 26ba1a3 (no sibling imports, per AGENTS.md):
- services/workflow/src/sentinel_workflow/domain/types.py  ModelResult, RefundAction
- services/workflow/src/sentinel_workflow/graph/nodes.py   plan() proposal defaults
- services/assistant/src/sentinel_assistant/adapters/http_reply.py  reply validation
"""

from __future__ import annotations

from typing import Any, Literal

import pytest
from pydantic import BaseModel, ConfigDict, Field

from tests.conftest import AUTH, draft, model_request


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class WorkflowModelResult(_Strict):
    outcome: Literal["PROPOSAL", "NEEDS_INPUT", "ESCALATE"]
    proposal: dict[str, Any] | None = None
    reason_codes: list[str]
    original_text: str
    language: str


class WorkflowRefundAction(_Strict):
    action: Literal["REQUEST_REFUND"] = "REQUEST_REFUND"
    case_id: str
    case_revision: int
    transaction_ref: str
    amount_minor: int = Field(ge=1)
    currency: Literal["INR"] = "INR"
    destination: Literal["ORIGINAL_PAYMENT_ROUTE"] = "ORIGINAL_PAYMENT_ROUTE"
    evidence_ids: list[str] = Field(min_length=1)
    policy_version: str


def workflow_plan_payload(proposal: dict[str, Any], state_evidence_ids: list[str]) -> dict:
    """Same defaults workflow plan() applies before policy/ledger."""
    payload = dict(proposal)
    payload.setdefault("case_id", "case-demo-42")
    payload.setdefault("case_revision", 1)
    payload.setdefault("evidence_ids", state_evidence_ids)
    payload.setdefault("policy_version", "demo-policy-v1")
    return payload


def assistant_accepts(data: Any) -> tuple[str, str]:
    """Mirror of HttpModelReply.generate validation."""
    assert isinstance(data, dict)
    reply, mode = data.get("text"), data.get("evidence_mode")
    assert isinstance(reply, str) and reply.strip()
    assert mode in {"sandbox", "recorded", "live", "fake"}
    return reply.strip(), mode


@pytest.mark.parametrize(
    "content",
    [
        draft(),
        draft(outcome="NEEDS_INPUT", transaction_ref=None, reason_codes=["AMBIGUOUS_TRANSACTION"]),
        draft(outcome="ESCALATE", reason_codes=["FRAUD_SIGNAL"]),
        draft(amount_minor=1),  # grounding escalation
    ],
)
def test_proposal_responses_validate_as_workflow_model_result(client, sarvam, content):
    sarvam.queue.append(content)
    request = model_request()
    response = client.post("/v1/proposals", json=request, headers=AUTH)
    assert response.status_code == 200  # 2xx => HttpModelAdapter validates the body
    result = WorkflowModelResult.model_validate(response.json())
    if result.outcome == "PROPOSAL":
        ids = [e["evidence_id"] for e in request["evidence"]]
        action = WorkflowRefundAction.model_validate(workflow_plan_payload(result.proposal, ids))
        assert action.amount_minor == 150000
        assert action.evidence_ids == ["evidence-payment-b", "evidence-order"]
    else:
        assert result.proposal is None


def test_model_outage_maps_to_workflow_peer_unavailable(client, sarvam):
    sarvam.queue.append(500)
    response = client.post("/v1/proposals", json=model_request(), headers=AUTH)
    assert response.status_code >= 500  # HttpModelAdapter => PeerUnavailableError (retry)


def test_unauthorized_maps_to_workflow_unauthorized(client):
    response = client.post("/v1/proposals", json=model_request())
    assert response.status_code in {401, 403}  # HttpModelAdapter => PeerError UNAUTHORIZED


def test_reply_validates_as_assistant_reply(client, sarvam):
    sarvam.queue.append('{"text": "  An operator will review your duplicate charge.  "}')
    response = client.post("/v1/replies", json={"text": "charged twice"})
    assert response.status_code == 200
    assert assistant_accepts(response.json()) == (
        "An operator will review your duplicate charge.",
        "live",
    )
