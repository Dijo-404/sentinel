"""POST /v1/replies: knowledge-grounded Sarvam replies, fail closed."""

from __future__ import annotations

import json

import httpx
import pytest


def test_reply_is_grounded_in_knowledge_hits(client, sarvam, knowledge):
    sarvam.queue.append('{"text": "Duplicate charges are reviewed by an operator."}')
    response = client.post("/v1/replies", json={"text": "  I was charged twice  "})
    assert response.status_code == 200
    assert response.json() == {
        "text": "Duplicate charges are reviewed by an operator.",
        "evidence_mode": "live",
    }
    [search] = knowledge.requests
    assert search.url.path == "/v1/search"
    assert search.url.params["q"] == "I was charged twice"
    assert search.headers["authorization"] == "Bearer knowledge-test-token"
    context = json.loads(sarvam.bodies()[0]["messages"][1]["content"])
    assert context["articles"] == [
        {
            "article_id": "article-demo-refund-policy",
            "title": "Sandbox refund policy",
            "summary": "Synthetic guidance for duplicate-charge refunds.",
        }
    ]
    assert context["user_message"] == "I was charged twice"


def test_no_hits_still_calls_model_with_empty_context(client, sarvam, knowledge):
    knowledge.hits = []
    sarvam.queue.append('{"text": "I do not know; an operator will follow up."}')
    assert client.post("/v1/replies", json={"text": "hi"}).status_code == 200
    assert json.loads(sarvam.bodies()[0]["messages"][1]["content"])["articles"] == []


@pytest.mark.parametrize("status", [401, 403, 500])
def test_knowledge_failure_is_503_and_skips_model(client, sarvam, knowledge, status):
    knowledge.status = status
    response = client.post("/v1/replies", json={"text": "hi"})
    assert response.status_code == 503
    assert sarvam.requests == []


@pytest.mark.parametrize("failure", [502, httpx.ReadTimeout("slow")])
def test_sarvam_failure_is_503(client, sarvam, failure):
    sarvam.queue.append(failure)
    assert client.post("/v1/replies", json={"text": "hi"}).status_code == 503


def test_malformed_twice_is_502_never_invented_text(client, sarvam):
    sarvam.queue.extend(["Hello!", '{"text": ""}'])
    response = client.post("/v1/replies", json={"text": "hi"})
    assert response.status_code == 502
    assert response.json()["code"] == "MODEL_OUTPUT_INVALID"
    assert len(sarvam.requests) == 2


@pytest.mark.parametrize("body", [{}, {"text": "   "}, {"text": 3}])
def test_empty_text_is_422(client, sarvam, body):
    assert client.post("/v1/replies", json=body).status_code == 422
    assert sarvam.requests == []
