"""Scheduled recheck idempotency and binding."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed

from tests.conftest import (
    ACTION_ID,
    CASE_ID,
    NOW,
    PROVIDER_REF,
    TENANT,
    auth_header,
    signed_webhook,
)

from sentinel_verifier.application.service import RECHECK_INTERVAL
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


def test_concurrent_recheck_same_idempotency_key_single_outcome(
    memory_client, tokens, verification_request
):
    """Only the insert winner processes; event_key stays stable without job_id."""
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
    memory_client.ledger.outcomes.clear()
    headers = {**auth_header(tokens["workflow"]), "Idempotency-Key": "recheck-concurrent"}

    def _post() -> dict:
        response = memory_client.post("/v1/rechecks", headers=headers, json=verification_request)
        return {"status_code": response.status_code, "body": response.json()}

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = [fut.result() for fut in as_completed([pool.submit(_post), pool.submit(_post)])]

    assert all(r["status_code"] == 202 for r in results)
    job_ids = {r["body"]["job_id"] for r in results}
    assert len(job_ids) == 1
    applied = [o for o in memory_client.ledger.outcomes if not o.get("noop")]
    assert len(applied) == 1
    assert applied[0]["event_key"] == f"verifier-{PROVIDER_REF}-PROVIDER_CONFIRMED"
    assert "job-" not in applied[0]["event_key"]
    assert memory_client.store.get_recheck_by_idempotency(TENANT, "recheck-concurrent") is not None
    assert len(memory_client.store.rechecks) == 1


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
    # Provider confirmed without credit stays WAITING — keep polling.
    assert job.status == "SCHEDULED"
    expected_at = (NOW + RECHECK_INTERVAL).isoformat().replace("+00:00", "Z")
    assert job.available_at == expected_at


def test_pending_recheck_stays_scheduled_not_completed(memory_client, tokens, verification_request):
    """Pending provider lookup must leave a future recheck, not mark complete empty."""
    response = memory_client.post(
        "/v1/rechecks",
        headers={**auth_header(tokens["workflow"]), "Idempotency-Key": "recheck-pending"},
        json=verification_request,
    )
    assert response.status_code == 202
    job_id = response.json()["job_id"]
    job = memory_client.store.get_recheck(TENANT, job_id)
    assert job is not None
    assert job.status == "SCHEDULED"
    assert job.attempts == 1
    expected_at = (NOW + RECHECK_INTERVAL).isoformat().replace("+00:00", "Z")
    assert job.available_at == expected_at
    assert memory_client.case_api.results == []
    assert memory_client.ledger.get_action(ACTION_ID)["status"] == "PENDING"


def test_credit_confirmed_recheck_delivers_case_result(
    memory_client, tokens, verification_request, credit_confirmed
):
    """Webhook/recheck CREDIT_CONFIRMED path must attempt case closure delivery."""
    del credit_confirmed
    response = memory_client.post(
        "/v1/rechecks",
        headers={**auth_header(tokens["workflow"]), "Idempotency-Key": "recheck-credit"},
        json=verification_request,
    )
    assert response.status_code == 202
    job = memory_client.store.get_recheck(TENANT, response.json()["job_id"])
    assert job is not None
    assert job.status == "COMPLETED"
    assert memory_client.ledger.get_action(ACTION_ID)["status"] == "CREDIT_CONFIRMED"
    assert len(memory_client.case_api.results) == 1
    announced = memory_client.case_api.results[0]
    assert announced["status"] == "VERIFIED_RESOLVED"
    assert announced["reason_code"] == "CREDIT_CONFIRMED"
    assert announced["event_key"] == f"verified-{ACTION_ID}-CREDIT_CONFIRMED"
    assert memory_client.case_api.cases[CASE_ID]["status"] == "VERIFIED_RESOLVED"


def test_webhook_credit_confirmed_delivers_case_result(
    memory_client, tokens, verification_request, webhook_body, credit_confirmed
):
    del credit_confirmed
    bind = memory_client.post(
        "/v1/rechecks",
        headers={**auth_header(tokens["workflow"]), "Idempotency-Key": "recheck-wh-bind"},
        json=verification_request,
    )
    assert bind.status_code == 202
    # Recheck already confirmed credit and announced; clear for webhook regression.
    memory_client.case_api.results.clear()
    memory_client.case_api.seed(CASE_ID, revision=1, status="WAITING_EXTERNAL")
    memory_client.ledger.seed_action(
        action_id=ACTION_ID, provider_ref=PROVIDER_REF, status="PROVIDER_CONFIRMED"
    )
    memory_client.ledger.outcomes.clear()

    raw, sig = signed_webhook(webhook_body)
    response = memory_client.post(
        "/v1/webhooks/simulator",
        content=raw,
        headers={"X-Sentinel-Signature": sig, "Content-Type": "application/json"},
    )
    assert response.status_code == 202
    assert memory_client.ledger.get_action(ACTION_ID)["status"] == "CREDIT_CONFIRMED"
    assert len(memory_client.case_api.results) == 1
    assert memory_client.case_api.results[0]["status"] == "VERIFIED_RESOLVED"


def test_credit_confirmed_case_api_unavailable_fails_closed(
    memory_client, tokens, verification_request, credit_confirmed
):
    del credit_confirmed
    memory_client.case_api.mode = "unavailable"
    response = memory_client.post(
        "/v1/rechecks",
        headers={**auth_header(tokens["workflow"]), "Idempotency-Key": "recheck-fail-closed"},
        json=verification_request,
    )
    assert response.status_code == 503
    assert memory_client.case_api.results == []
