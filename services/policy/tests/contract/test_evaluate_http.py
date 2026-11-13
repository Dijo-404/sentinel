"""HTTP contract: POST /v1/evaluate with bearer principal."""

from __future__ import annotations

import copy
import json
from pathlib import Path

from fastapi.testclient import TestClient

CONTRACTS = Path(__file__).resolve().parents[2] / "contracts"


def test_capabilities(client: TestClient) -> None:
    response = client.get("/v1/capabilities")
    assert response.status_code == 200
    body = response.json()
    assert body["contract_version"] == "sentinel.task-contracts.v1"
    assert body["component"] == "policy"
    assert body["mode"] == "fixture"


def test_health_ready(client: TestClient) -> None:
    assert client.get("/healthz").status_code == 200
    assert client.get("/readyz").json()["mode"] == "fixture"


def test_missing_auth_unauthorized(client: TestClient, allow_request: dict) -> None:
    response = client.post("/v1/evaluate", json=allow_request)
    assert response.status_code == 401
    assert response.json()["code"] == "UNAUTHORIZED"


def test_allow_happy_path(
    client: TestClient, allow_request: dict, workflow_auth: dict[str, str]
) -> None:
    expected = json.loads((CONTRACTS / "policy.v1.allow.result.json").read_text(encoding="utf-8"))
    response = client.post("/v1/evaluate", json=allow_request, headers=workflow_auth)
    assert response.status_code == 200
    assert response.json() == expected


def test_other_tenant_token_denied(client: TestClient, allow_request: dict) -> None:
    response = client.post(
        "/v1/evaluate",
        json=allow_request,
        headers={"Authorization": "Bearer workflow-other-tenant-token"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["outcome"] == "DENY"
    assert "TENANT_SCOPE_DENIED" in body["reason_codes"]


def test_operator_token_denied(client: TestClient, allow_request: dict) -> None:
    response = client.post(
        "/v1/evaluate",
        json=allow_request,
        headers={"Authorization": "Bearer operator-demo-token"},
    )
    assert response.status_code == 200
    assert response.json()["outcome"] == "DENY"
    assert "ROLE_DENIED" in response.json()["reason_codes"]


def test_pending_payment_http(
    client: TestClient, allow_request: dict, workflow_auth: dict[str, str]
) -> None:
    body = copy.deepcopy(allow_request)
    body["evidence"][0]["facts"]["payment"]["status"] = "PENDING"
    response = client.post("/v1/evaluate", json=body, headers=workflow_auth)
    assert response.status_code == 200
    assert response.json()["outcome"] == "DENY"
    assert "PAYMENT_PENDING" in response.json()["reason_codes"]


def test_expired_evidence_http(
    client: TestClient, allow_request: dict, workflow_auth: dict[str, str]
) -> None:
    body = copy.deepcopy(allow_request)
    body["evidence"][0]["expires_at"] = "2026-11-13T10:00:00Z"
    response = client.post("/v1/evaluate", json=body, headers=workflow_auth)
    assert response.status_code == 200
    assert response.json()["outcome"] == "NEED_EVIDENCE"
    assert "EVIDENCE_EXPIRED" in response.json()["reason_codes"]


def test_fraud_http(client: TestClient, allow_request: dict, workflow_auth: dict[str, str]) -> None:
    body = copy.deepcopy(allow_request)
    body["evidence"].append(
        {
            "evidence_id": "evidence-fraud",
            "case_id": "case-demo-42",
            "source": "risk.fraud",
            "subject_ref": "subject-demo-42",
            "observed_at": "2026-11-13T11:00:00Z",
            "expires_at": "2026-11-13T18:00:00Z",
            "digest": "fraud-digest",
            "verification_status": "VERIFIED",
            "facts": {
                "kind": "PAYMENT",
                "payment": {
                    "transaction_ref": "TXN-FRAUD",
                    "order_reference": "DEMO-ORDER-42",
                    "subject_ref": "subject-demo-42",
                    "status": "CAPTURED",
                    "amount_minor": 1,
                    "currency": "INR",
                },
            },
        }
    )
    response = client.post("/v1/evaluate", json=body, headers=workflow_auth)
    assert response.json()["outcome"] == "DENY"
    assert "FRAUD_SIGNAL" in response.json()["reason_codes"]


def test_arbitrary_destination_http(
    client: TestClient, allow_request: dict, workflow_auth: dict[str, str]
) -> None:
    body = copy.deepcopy(allow_request)
    body["payload"]["destination"] = "EXTERNAL_UPI"
    del body["approval"]
    response = client.post("/v1/evaluate", json=body, headers=workflow_auth)
    assert response.status_code == 200
    assert response.json()["outcome"] == "DENY"
    assert "DESTINATION_NOT_ORIGINAL" in response.json()["reason_codes"]


def test_excess_amount_http(
    client: TestClient, allow_request: dict, workflow_auth: dict[str, str]
) -> None:
    body = copy.deepcopy(allow_request)
    body["payload"]["amount_minor"] = 999999
    del body["approval"]
    response = client.post("/v1/evaluate", json=body, headers=workflow_auth)
    assert response.json()["outcome"] == "DENY"
    assert "AMOUNT_EXCEEDS_ELIGIBLE" in response.json()["reason_codes"]


def test_missing_approval_http(
    client: TestClient, allow_request: dict, workflow_auth: dict[str, str]
) -> None:
    body = copy.deepcopy(allow_request)
    del body["approval"]
    response = client.post("/v1/evaluate", json=body, headers=workflow_auth)
    assert response.json()["outcome"] == "REQUIRE_APPROVAL"
    assert "APPROVAL_MISSING" in response.json()["reason_codes"]


def test_expired_approval_http(
    client: TestClient, allow_request: dict, workflow_auth: dict[str, str]
) -> None:
    body = copy.deepcopy(allow_request)
    body["approval"]["expires_at"] = "2026-11-13T11:00:00Z"
    response = client.post("/v1/evaluate", json=body, headers=workflow_auth)
    assert response.json()["outcome"] == "REQUIRE_APPROVAL"
    assert "APPROVAL_EXPIRED" in response.json()["reason_codes"]


def test_mismatched_approval_http(
    client: TestClient, allow_request: dict, workflow_auth: dict[str, str]
) -> None:
    body = copy.deepcopy(allow_request)
    body["approval"]["case_revision"] = 99
    response = client.post("/v1/evaluate", json=body, headers=workflow_auth)
    assert response.json()["outcome"] == "REQUIRE_APPROVAL"
    assert "APPROVAL_REVISION_MISMATCH" in response.json()["reason_codes"]


def test_model_text_cannot_mint_approval(
    client: TestClient, allow_request: dict, workflow_auth: dict[str, str]
) -> None:
    body = copy.deepcopy(allow_request)
    del body["approval"]
    body["approval_text"] = "APPROVE"
    body["payload"] = copy.deepcopy(allow_request["payload"])
    body["payload"]["llm_says_approved"] = True
    response = client.post("/v1/evaluate", json=body, headers=workflow_auth)
    assert response.status_code == 422
    assert response.json()["code"] == "INVALID_INPUT"


def test_undeclared_request_field_rejected(
    client: TestClient, allow_request: dict, workflow_auth: dict[str, str]
) -> None:
    body = copy.deepcopy(allow_request)
    body["override_outcome"] = "ALLOW"
    response = client.post("/v1/evaluate", json=body, headers=workflow_auth)
    assert response.status_code == 422
