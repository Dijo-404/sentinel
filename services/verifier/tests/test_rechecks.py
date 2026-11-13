"""Scheduled recheck idempotency and binding."""

from __future__ import annotations

from tests.conftest import auth_header


def test_recheck_returns_ack_202(memory_client, tokens, verification_request):
    response = memory_client.post(
        "/v1/rechecks",
        headers={**auth_header(tokens["workflow"]), "Idempotency-Key": "recheck-1"},
        json=verification_request,
    )
    assert response.status_code == 202
    body = response.json()
    assert body["accepted"] is True
    assert body["contract_version"] == "sentinel.task-contracts.v1"
    assert body["job_id"].startswith("job-")


def test_recheck_idempotent_replay(memory_client, tokens, verification_request):
    headers = {**auth_header(tokens["workflow"]), "Idempotency-Key": "recheck-same"}
    first = memory_client.post("/v1/rechecks", headers=headers, json=verification_request)
    second = memory_client.post("/v1/rechecks", headers=headers, json=verification_request)
    assert first.status_code == 202
    assert second.status_code == 202
    assert first.json()["job_id"] == second.json()["job_id"]


def test_recheck_idempotency_conflict(memory_client, tokens, verification_request):
    headers = {**auth_header(tokens["workflow"]), "Idempotency-Key": "recheck-conflict"}
    first = memory_client.post("/v1/rechecks", headers=headers, json=verification_request)
    assert first.status_code == 202
    altered = {**verification_request, "provider_ref": "refund-other"}
    second = memory_client.post("/v1/rechecks", headers=headers, json=altered)
    assert second.status_code == 409
    assert second.json()["code"] == "IDEMPOTENCY_CONFLICT"


def test_recheck_requires_idempotency_key(memory_client, tokens, verification_request):
    response = memory_client.post(
        "/v1/rechecks",
        headers=auth_header(tokens["workflow"]),
        json=verification_request,
    )
    assert response.status_code == 422


def test_verifier_role_may_schedule_recheck(memory_client, tokens, verification_request):
    response = memory_client.post(
        "/v1/rechecks",
        headers={**auth_header(tokens["verifier"]), "Idempotency-Key": "recheck-verifier"},
        json=verification_request,
    )
    assert response.status_code == 202
