"""HTTP surface: auth gate, draft lifecycle, capabilities labeling."""

from __future__ import annotations

from fastapi.testclient import TestClient

from sentinel_merchant_comms.adapters.auth import TokenMapAuth
from sentinel_merchant_comms.adapters.http_api import create_app
from sentinel_merchant_comms.adapters.memory_store import (
    FixedClock,
    InMemoryDraftStore,
    SequentialIds,
)
from sentinel_merchant_comms.application.service import MerchantCommsService
from sentinel_merchant_comms.domain.templates import FAKE_LABEL
from tests.stubs.case_api import ValidCaseApi


def _client() -> TestClient:
    service = MerchantCommsService(
        case_api=ValidCaseApi(),
        indic=None,
        store=InMemoryDraftStore(),
        clock=FixedClock(),
        ids=SequentialIds(),
    )
    auth = TokenMapAuth(
        {
            "operator-token": {
                "principal_id": "op-demo",
                "tenant_id": "tenant-demo",
                "roles": ["operator"],
                "subject_refs": ["subject-demo"],
                "case_ids": ["case-demo-42"],
            }
        }
    )
    return TestClient(create_app(service=service, auth=auth, mode="fixture"))


def test_capabilities_and_health() -> None:
    client = _client()
    assert client.get("/healthz").json()["status"] == "ok"
    caps = client.get("/v1/capabilities").json()
    assert caps["port"] == "merchant-comms.v1"
    assert caps["mode"] == "fixture"


def test_http_draft_lifecycle_requires_auth() -> None:
    client = _client()
    denied = client.post("/v1/drafts", json={"case_id": "case-demo-42", "language": "en"})
    assert denied.status_code == 401

    headers = {"Authorization": "Bearer operator-token"}
    created = client.post(
        "/v1/drafts",
        headers=headers,
        json={"case_id": "case-demo-42", "language": "en"},
    )
    assert created.status_code == 200
    draft = created.json()
    assert draft["status"] == "DRAFT"
    assert FAKE_LABEL in draft["body"]

    too_soon = client.post(
        f"/v1/drafts/{draft['draft_id']}/simulate-send",
        headers=headers,
        json={},
    )
    assert too_soon.status_code == 409
    assert too_soon.json()["code"] == "APPROVAL_REQUIRED"

    approved = client.post(
        f"/v1/drafts/{draft['draft_id']}/decisions",
        headers=headers,
        json={"decision": "APPROVE"},
    )
    assert approved.json()["status"] == "APPROVED"

    sent = client.post(
        f"/v1/drafts/{draft['draft_id']}/simulate-send",
        headers=headers,
        json={"channel": "sms"},
    )
    body = sent.json()
    assert body["status"] == "SIMULATED_SENT"
    assert body["delivery_history"][0]["channel"] == "sms"


def test_http_reject_blocks_send() -> None:
    client = _client()
    headers = {"Authorization": "Bearer operator-token"}
    draft = client.post(
        "/v1/drafts",
        headers=headers,
        json={"case_id": "case-demo-42", "language": "ta"},
    ).json()
    client.post(
        f"/v1/drafts/{draft['draft_id']}/decisions",
        headers=headers,
        json={"decision": "REJECT"},
    )
    blocked = client.post(
        f"/v1/drafts/{draft['draft_id']}/simulate-send",
        headers=headers,
        json={},
    )
    assert blocked.status_code == 409
    assert blocked.json()["code"] == "DRAFT_REJECTED"
