"""Live Sarvam smoke test. Skipped unless MODEL_GATEWAY_LIVE_TEST=1 and SARVAM_API_KEY are set."""

from __future__ import annotations

import os

import pytest

from sentinel_model_gateway.adapters.sarvam import SarvamChat
from sentinel_model_gateway.application.service import ProposalService, ReplyService
from sentinel_model_gateway.domain.types import ModelRequest
from tests.conftest import model_request

pytestmark = pytest.mark.skipif(
    os.environ.get("MODEL_GATEWAY_LIVE_TEST") != "1" or not os.environ.get("SARVAM_API_KEY"),
    reason="live Sarvam test disabled (set MODEL_GATEWAY_LIVE_TEST=1 and SARVAM_API_KEY)",
)


def _chat() -> SarvamChat:
    return SarvamChat(
        os.environ["SARVAM_API_KEY"],
        os.environ.get("MODEL_GATEWAY_MODEL", "sarvam-105b"),
        timeout_s=60.0,
        reasoning_effort=os.environ.get("MODEL_GATEWAY_LIVE_REASONING_EFFORT") or None,
    )


def test_live_proposal_is_grounded():
    result = ProposalService(_chat()).propose(ModelRequest.model_validate(model_request()))
    print("live proposal:", result.model_dump(exclude_none=True))
    assert result.outcome in {"PROPOSAL", "NEEDS_INPUT", "ESCALATE"}
    if result.outcome == "PROPOSAL":
        assert result.proposal["amount_minor"] == 150000
        assert result.proposal["transaction_ref"] in {"TXN-A", "TXN-B"}


class _StaticKnowledge:
    def search(self, query: str):
        return [
            {
                "article_id": "article-demo-refund-policy",
                "title": "Sandbox refund policy",
                "summary": "Duplicate charges are reviewed by an operator before any refund.",
            }
        ]


def test_live_reply():
    text = ReplyService(_chat(), _StaticKnowledge()).reply("मुझसे दो बार पैसे कटे")
    print("live reply:", text)
    assert text.strip()
