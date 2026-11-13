"""Scheduled recheck idempotency and binding."""

from __future__ import annotations

from tests.conftest import ACTION_ID, CASE_ID, PROVIDER_REF, TENANT, auth_header

from sentinel_verifier.domain.types import ProviderBinding, RecheckJob, Refund


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


def test_drain_due_rechecks_processes_scheduled_job(memory_client, tokens):
    memory_client.provider.seed_refund(
        Refund(
            action_id=ACTION_ID,
            provider_ref=PROVIDER_REF,
            transaction_ref="TXN-B",
            amount_minor=150000,
            currency="INR",
            status="PROVIDER_CONFIRMED",
        )
    )
    memory_client.store.save_binding(
        ProviderBinding(
            tenant_id=TENANT,
            provider_ref=PROVIDER_REF,
            action_id=ACTION_ID,
            case_id=CASE_ID,
            case_revision=1,
            updated_at="2026-11-13T11:00:00Z",
        )
    )
    memory_client.store.save_recheck(
        RecheckJob(
            tenant_id=TENANT,
            job_id="job-drain-1",
            idempotency_key="drain-key-1",
            case_id=CASE_ID,
            case_revision=1,
            action_id=ACTION_ID,
            provider_ref=PROVIDER_REF,
            request_digest="digest-drain",
            available_at="2026-11-13T11:00:00Z",
            lease_expires_at="2026-11-13T11:05:00Z",
            attempts=0,
            status="SCHEDULED",
            created_at="2026-11-13T11:00:00Z",
            updated_at="2026-11-13T11:00:00Z",
        )
    )
    memory_client.ledger.outcomes.clear()
    response = memory_client.post(
        "/v1/rechecks/drain",
        headers=auth_header(tokens["verifier"]),
    )
    assert response.status_code == 200
    assert response.json()["drained"] == 1
    assert len(memory_client.ledger.outcomes) == 1
    job = memory_client.store.get_recheck(TENANT, "job-drain-1")
    assert job is not None
    assert job.status == "COMPLETED"
