"""Webhook signature, tenant mapping, replay, and durable inbox behavior."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from tests.conftest import (
    ACTION_ID,
    HMAC_KEY,
    MERCHANT,
    PROVIDER_REF,
    TENANT,
    auth_header,
    signed_webhook,
)

from sentinel_verifier.adapters.auth_tokens import TokenPrincipalMap, demo_principals
from sentinel_verifier.adapters.ids import SequenceIdGenerator
from sentinel_verifier.adapters.postgres_store import PostgresVerifierStore
from sentinel_verifier.bootstrap import build_app
from sentinel_verifier.domain.types import Credit, InboxRecord, Refund


@pytest.mark.postgres
def test_bad_signature_rejected(pg_client, webhook_body):
    raw, _sig = signed_webhook(webhook_body)
    response = pg_client.post(
        "/v1/webhooks/simulator",
        content=raw,
        headers={"X-Sentinel-Signature": "deadbeef", "Content-Type": "application/json"},
    )
    assert response.status_code == 401
    assert response.json()["code"] == "UNAUTHORIZED"


@pytest.mark.postgres
def test_tenant_mapping_rejected(pg_client, webhook_body):
    body = {**webhook_body, "tenant_id": "tenant-other"}
    raw, sig = signed_webhook(body)
    response = pg_client.post(
        "/v1/webhooks/simulator",
        content=raw,
        headers={"X-Sentinel-Signature": sig, "Content-Type": "application/json"},
    )
    assert response.status_code == 403


@pytest.mark.postgres
def test_replay_age_rejected_when_enforced(engine, clock, peers, webhook_body):
    eng, schema = engine
    provider, ledger, evidence, case_api = peers
    store = PostgresVerifierStore(eng, schema=schema)
    app = build_app(
        store=store,
        provider=provider,
        ledger=ledger,
        evidence=evidence,
        case_api=case_api,
        auth=TokenPrincipalMap(demo_principals(TENANT)),
        clock=clock,
        ids=SequenceIdGenerator(),
        mode="fixture",
        webhook_hmac_key=HMAC_KEY,
        merchant_map={MERCHANT: TENANT},
        enforce_event_age=True,
    )
    client = TestClient(app)
    body = {
        **webhook_body,
        "occurred_at": datetime(2026, 11, 10, 12, 0, 0, tzinfo=UTC)
        .isoformat()
        .replace("+00:00", "Z"),
    }
    raw, sig = signed_webhook(body)
    response = client.post(
        "/v1/webhooks/simulator",
        content=raw,
        headers={"X-Sentinel-Signature": sig, "Content-Type": "application/json"},
    )
    assert response.status_code == 422
    assert response.json()["code"] == "REPLAY_REJECTED"


@pytest.mark.postgres
def test_unprocessed_duplicate_reprocesses(pg_client, webhook_body, tokens, verification_request):
    bind = pg_client.post(
        "/v1/rechecks",
        headers={**auth_header(tokens["workflow"]), "Idempotency-Key": "recheck-crash-1"},
        json=verification_request,
    )
    assert bind.status_code == 202
    pg_client.provider.seed_refund(
        Refund(
            action_id=ACTION_ID,
            provider_ref=PROVIDER_REF,
            transaction_ref="TXN-B",
            amount_minor=150000,
            currency="INR",
            status="PROVIDER_CONFIRMED",
        )
    )
    pg_client.ledger.outcomes.clear()
    raw, sig = signed_webhook(webhook_body)
    crash_record = InboxRecord(
        tenant_id=TENANT,
        event_id=webhook_body["event_id"],
        provider="simulator",
        provider_ref=PROVIDER_REF,
        event_type="REFUND_STATUS",
        merchant_ref=MERCHANT,
        occurred_at=webhook_body["occurred_at"],
        payload_json=raw.decode("utf-8"),
        signature_hex=sig,
        received_at="2026-11-13T11:59:00Z",
        processed_at=None,
        process_status="ACCEPTED",
        reason_code=None,
    )
    inserted = pg_client.store.insert_inbox(crash_record)
    assert inserted.duplicate is False
    assert inserted.process_status == "ACCEPTED"

    second = pg_client.post(
        "/v1/webhooks/simulator",
        content=raw,
        headers={"X-Sentinel-Signature": sig, "Content-Type": "application/json"},
    )
    assert second.status_code == 202
    assert second.json() == {"accepted": True}
    assert len(pg_client.ledger.outcomes) == 1
    stored = pg_client.store.get_inbox(TENANT, webhook_body["event_id"])
    assert stored is not None
    assert stored.process_status == "PROCESSED"


@pytest.mark.postgres
def test_inbox_deduplicates_without_extra_ledger_write(
    pg_client, webhook_body, tokens, verification_request
):
    bind = pg_client.post(
        "/v1/rechecks",
        headers={**auth_header(tokens["workflow"]), "Idempotency-Key": "recheck-bind-1"},
        json=verification_request,
    )
    assert bind.status_code == 202
    pg_client.ledger.outcomes.clear()

    pg_client.provider.seed_refund(
        Refund(
            action_id=ACTION_ID,
            provider_ref=PROVIDER_REF,
            transaction_ref="TXN-B",
            amount_minor=150000,
            currency="INR",
            status="PROVIDER_CONFIRMED",
        )
    )

    raw, sig = signed_webhook(webhook_body)
    first = pg_client.post(
        "/v1/webhooks/simulator",
        content=raw,
        headers={"X-Sentinel-Signature": sig, "Content-Type": "application/json"},
    )
    assert first.status_code == 202
    assert first.json() == {"accepted": True}
    assert len(pg_client.ledger.outcomes) == 1

    second = pg_client.post(
        "/v1/webhooks/simulator",
        content=raw,
        headers={"X-Sentinel-Signature": sig, "Content-Type": "application/json"},
    )
    assert second.status_code == 202
    assert second.json() == {"accepted": True}
    assert len(pg_client.ledger.outcomes) == 1
    stored = pg_client.store.get_inbox(TENANT, webhook_body["event_id"])
    assert stored is not None


@pytest.mark.postgres
def test_out_of_order_events_reconcile_current_provider_status(
    pg_client, tokens, verification_request
):
    bind = pg_client.post(
        "/v1/rechecks",
        headers={**auth_header(tokens["workflow"]), "Idempotency-Key": "recheck-ooo-1"},
        json=verification_request,
    )
    assert bind.status_code == 202

    pg_client.provider.seed_refund(
        Refund(
            action_id=ACTION_ID,
            provider_ref=PROVIDER_REF,
            transaction_ref="TXN-B",
            amount_minor=150000,
            currency="INR",
            status="PROVIDER_CONFIRMED",
        )
    )
    pg_client.provider.seed_credit(
        Credit(provider_ref=PROVIDER_REF, confirmed=True, observed_at="2026-11-13T12:00:00Z")
    )

    older = {
        "event_id": "evt-older",
        "tenant_id": TENANT,
        "merchant_ref": MERCHANT,
        "provider_ref": PROVIDER_REF,
        "type": "REFUND_STATUS",
        "occurred_at": "2026-11-13T11:00:00Z",
    }
    newer = {
        "event_id": "evt-newer",
        "tenant_id": TENANT,
        "merchant_ref": MERCHANT,
        "provider_ref": PROVIDER_REF,
        "type": "CREDIT_STATUS",
        "occurred_at": "2026-11-13T11:30:00Z",
    }
    for body in (newer, older):
        raw, sig = signed_webhook(body)
        response = pg_client.post(
            "/v1/webhooks/simulator",
            content=raw,
            headers={"X-Sentinel-Signature": sig, "Content-Type": "application/json"},
        )
        assert response.status_code == 202

    action = pg_client.ledger.get_action(ACTION_ID)
    assert action["status"] == "CREDIT_CONFIRMED"
    assert pg_client.provider.lookup_calls


@pytest.mark.postgres
def test_claimed_event_type_alone_does_not_confirm(
    pg_client, webhook_body, tokens, verification_request
):
    bind = pg_client.post(
        "/v1/rechecks",
        headers={**auth_header(tokens["workflow"]), "Idempotency-Key": "recheck-claim-1"},
        json=verification_request,
    )
    assert bind.status_code == 202
    pg_client.ledger.outcomes.clear()
    body = {**webhook_body, "event_id": "evt-claim-only"}
    raw, sig = signed_webhook(body)
    response = pg_client.post(
        "/v1/webhooks/simulator",
        content=raw,
        headers={"X-Sentinel-Signature": sig, "Content-Type": "application/json"},
    )
    assert response.status_code == 202
    assert pg_client.ledger.get_action(ACTION_ID)["status"] == "PENDING"
    assert pg_client.ledger.reservation_held(ACTION_ID)
    assert not [o for o in pg_client.ledger.outcomes if o.get("status") == "PROVIDER_CONFIRMED"]
