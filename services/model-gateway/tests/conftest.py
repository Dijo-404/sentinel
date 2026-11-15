"""Test doubles: controlled Sarvam and knowledge HTTP transports (tests only, never runtime)."""

from __future__ import annotations

import copy
import json
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

from sentinel_model_gateway.bootstrap import Settings, build_app

PROPOSAL_TOKEN = "tok-gateway-test"
FAKE_KEY = "sk-test-not-a-real-key"


def _payment(evidence_id: str, ref: str, amount: int = 150000) -> dict[str, Any]:
    return {
        "evidence_id": evidence_id,
        "case_id": "case-demo-42",
        "source": "simulator",
        "subject_ref": "subject-demo",
        "observed_at": "2026-11-15T00:00:00Z",
        "expires_at": "2026-11-15T01:00:00Z",
        "digest": "a" * 64,
        "verification_status": "VERIFIED",
        "facts": {
            "kind": "PAYMENT",
            "payment": {
                "transaction_ref": ref,
                "order_reference": "DEMO-ORDER-42",
                "subject_ref": "subject-demo",
                "status": "CAPTURED",
                "amount_minor": amount,
                "currency": "INR",
            },
        },
    }


# Mirrors the workflow FixtureEvidence duplicate-payment bundle and a real ModelRequest dump.
MODEL_REQUEST: dict[str, Any] = {
    "case": {
        "contract_version": "sentinel.task-contracts.v1",
        "case_id": "case-demo-42",
        "revision": 1,
        "status": "RECONCILING",
        "language": "en-IN",
        "intent": "DUPLICATE_PAYMENT",
        "evidence_ids": [],
    },
    "input": {
        "case_id": "case-demo-42",
        "case_revision": 1,
        "original_text": "I was charged twice for order DEMO-ORDER-42",
        "language": "en-IN",
        "order_reference": "DEMO-ORDER-42",
        "messages": [
            {
                "message_id": "m1",
                "text": "I was charged twice for order DEMO-ORDER-42",
                "language": "en-IN",
                "author": "CUSTOMER",
                "occurred_at": "2026-11-15T00:00:00Z",
            }
        ],
    },
    "evidence": [
        _payment("evidence-payment-a", "TXN-A"),
        _payment("evidence-payment-b", "TXN-B"),
        {
            **_payment("evidence-order", "unused"),
            "facts": {
                "kind": "ORDER",
                "order": {
                    "order_reference": "DEMO-ORDER-42",
                    "fulfilled_order_count": 1,
                    "merchant_confirmed_duplicate": True,
                    "paid": True,
                },
            },
        },
    ],
}


def model_request() -> dict[str, Any]:
    return copy.deepcopy(MODEL_REQUEST)


def draft(**overrides: Any) -> str:
    body = {
        "outcome": "PROPOSAL",
        "transaction_ref": "TXN-B",
        "amount_minor": 150000,
        "evidence_ids": ["evidence-payment-b", "evidence-order"],
        "reason_codes": ["DUPLICATE_PAYMENT"],
    }
    body.update(overrides)
    return json.dumps(body)


class FakeSarvam:
    """Queue of responses: str => chat content, int => HTTP status, Exception => raised."""

    def __init__(self) -> None:
        self.queue: list[Any] = []
        self.requests: list[httpx.Request] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        item = self.queue.pop(0)
        if isinstance(item, Exception):
            raise item
        if isinstance(item, int):
            return httpx.Response(item, json={"error": "upstream"})
        return httpx.Response(200, json={"choices": [{"message": {"content": item}}]})

    def bodies(self) -> list[dict[str, Any]]:
        return [json.loads(r.content) for r in self.requests]


class FakeKnowledge:
    def __init__(self) -> None:
        self.status = 200
        self.hits = [
            {
                "article_id": "article-demo-refund-policy",
                "title": "Sandbox refund policy",
                "summary": "Synthetic guidance for duplicate-charge refunds.",
                "updated_at": "2026-11-14T10:00:00Z",
            }
        ]
        self.requests: list[httpx.Request] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if self.status != 200:
            return httpx.Response(self.status, json={"code": "X"})
        return httpx.Response(200, json={"hits": self.hits})


@pytest.fixture
def sarvam() -> FakeSarvam:
    return FakeSarvam()


@pytest.fixture
def knowledge() -> FakeKnowledge:
    return FakeKnowledge()


@pytest.fixture
def client(sarvam: FakeSarvam, knowledge: FakeKnowledge) -> TestClient:
    settings = Settings.from_environ(
        {
            "SARVAM_API_KEY": FAKE_KEY,
            "MODEL_GATEWAY_MODEL": "sarvam-test-model",
            "MODEL_GATEWAY_TOKENS": PROPOSAL_TOKEN,
            "MODEL_GATEWAY_KNOWLEDGE_URL": "http://knowledge.test",
            "MODEL_GATEWAY_KNOWLEDGE_TOKEN": "knowledge-test-token",
        }
    )
    app = build_app(
        settings,
        sarvam_client=httpx.Client(transport=httpx.MockTransport(sarvam.handler)),
        knowledge_client=httpx.Client(transport=httpx.MockTransport(knowledge.handler)),
    )
    return TestClient(app)


AUTH = {"Authorization": f"Bearer {PROPOSAL_TOKEN}"}
