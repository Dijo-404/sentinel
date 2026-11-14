"""Invitation delivery outbox + sandbox inbox (finding #11)."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi.testclient import TestClient
from tests.conftest import auth_header, login

from sentinel_identity.adapters.clock import SystemClock
from sentinel_identity.adapters.delivery_sandbox import SandboxDeliveryAdapter
from sentinel_identity.adapters.storage_memory import MemoryIdentityStore
from sentinel_identity.application.service import IdentityService
from sentinel_identity.bootstrap import Settings, build_app
from sentinel_identity.domain.models import Invitation


def _invite(client: TestClient, demo_password: str, *, email: str, key: str) -> dict:
    admin = login(client, "admin@example.test", demo_password, requested_role="platform_admin")
    response = client.post(
        "/v1/admin/invitations",
        headers=auth_header(admin["session_token"]),
        json={
            "display_name": "Delivery Op",
            "work_email": email,
            "tenant_id": "tenant-demo",
            "role_id": "operator",
            "idempotency_key": key,
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["delivery_hint"] == "queued_for_delivery_adapter"
    assert "invite_token" not in body
    return body


def test_acceptance_link_in_sandbox_inbox_after_invite(
    client: TestClient, store: MemoryIdentityStore, demo_password: str
) -> None:
    email = "delivery-op@example.test"
    body = _invite(client, demo_password, email=email, key="delivery-inbox-001")
    inv_id = body["invitation"]["invitation_id"]
    token = store.peek_delivery_secret(inv_id)
    assert token

    inbox = client.get("/v1/sandbox/inbox", params={"email": email})
    assert inbox.status_code == 200
    payload = inbox.json()
    assert payload["evidence_label"] == "sandbox_inbox"
    assert len(payload["messages"]) == 1
    message = payload["messages"][0]
    assert message["invitation_id"] == inv_id
    assert message["token"] == token
    assert message["acceptance_link"].endswith(f"/auth/accept-invitation?token={token}")
    assert token in message["acceptance_link"]


def test_invite_delivery_survives_restart_simulation(
    store: MemoryIdentityStore, demo_password: str
) -> None:
    """Durable outbox lives on the store; new process (new adapter/service) still reads it."""
    app = build_app(
        Settings(
            mode="fixture",
            contract_version="sentinel.task-contracts.v1",
            database_url="",
            seed=False,
            accept_link_base="http://127.0.0.1:3000",
        ),
        store=store,
    )
    client = TestClient(app)
    email = "restart-op@example.test"
    body = _invite(client, demo_password, email=email, key="delivery-restart-001")
    inv_id = body["invitation"]["invitation_id"]
    original_token = store.peek_delivery_secret(inv_id)
    assert original_token

    # Simulate process restart: new clock/adapter/service, same durable store.
    clock = SystemClock()
    restarted = IdentityService(
        store,
        clock,
        delivery=SandboxDeliveryAdapter(store, clock, accept_link_base="http://127.0.0.1:3000"),
    )
    assert restarted.flush_delivery_outbox()["delivered"] == 0  # already drained
    inbox = restarted.list_sandbox_inbox(work_email=email)
    assert len(inbox["messages"]) == 1
    assert inbox["messages"][0]["token"] == original_token
    assert original_token in inbox["messages"][0]["acceptance_link"]

    # Hand off only durable delivery maps to a fresh store instance (DB restart stand-in).
    handed = MemoryIdentityStore()
    handed._delivery_outbox = dict(store._delivery_outbox)
    handed._delivery_by_invitation = dict(store._delivery_by_invitation)
    assert handed.peek_delivery_secret(inv_id) == original_token
    assert handed.list_sandbox_inbox(work_email=email)[0].raw_token == original_token


def test_pending_outbox_drains_into_inbox_after_crash_before_drain(
    store: MemoryIdentityStore,
) -> None:
    now = datetime.now(UTC)
    invitation = Invitation(
        invitation_id="11111111-1111-1111-1111-111111111111",
        work_email="pending-drain@example.test",
        display_name="Pending",
        tenant_id="tenant-demo",
        role_id="operator",
        scope_key="tenant:tenant-demo",
        token_hash="hash-not-used",
        status="pending",
        invited_by="22222222-2222-2222-2222-222222222222",
        created_at=now,
        expires_at=now,
        idempotency_key="pending-drain-key",
    )
    store.invitations[invitation.invitation_id] = invitation
    raw = "raw-token-for-drain-test"
    store.record_delivery_secret(invitation.invitation_id, raw, work_email=invitation.work_email)
    assert store.list_pending_deliveries()
    assert store.list_sandbox_inbox() == ()

    clock = SystemClock()
    delivered = SandboxDeliveryAdapter(store, clock).drain()
    assert delivered == 1
    assert store.list_pending_deliveries() == ()
    messages = store.list_sandbox_inbox(work_email=invitation.work_email)
    assert len(messages) == 1
    assert messages[0].raw_token == raw
    assert messages[0].acceptance_link is not None
    assert raw in messages[0].acceptance_link


def test_postgres_store_does_not_cache_delivery_in_process_memory() -> None:
    from unittest.mock import MagicMock

    from sqlalchemy.engine import Engine

    from sentinel_identity.adapters.storage_postgres import PostgresIdentityStore

    engine = MagicMock(spec=Engine)
    store = PostgresIdentityStore(engine)
    assert not hasattr(store, "_delivery_secrets")
