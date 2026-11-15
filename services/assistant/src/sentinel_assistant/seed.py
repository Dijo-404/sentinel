"""Sandbox seed: ≥1 thread + message for tenant-demo."""

from __future__ import annotations

from typing import Any

from .adapters.sandbox_reply import SandboxEchoReply
from .adapters.storage_postgres import PostgresAssistantStore, build_engine
from .application.errors import ConfigurationError
from .domain.types import Message, Thread

SEED_TENANT_ID = "tenant-demo"
SEED_THREAD_ID = "thr-seed-tenant-demo"
SEED_MESSAGE_ID = "msg-seed-tenant-demo-user"
SEED_REPLY_ID = "msg-seed-tenant-demo-assistant"
SEED_CREATED_AT = "2026-11-15T10:00:00Z"
SEED_TITLE = "Sandbox assistant thread"
SEED_USER_TEXT = "Hello from tenant-demo sandbox seed."
SEED_EVIDENCE_MODE = "sandbox"


def seed_demo_threads(database_url: str) -> dict[str, Any]:
    """Write synthetic assistant rows for portal real-peers. Requires ASSISTANT_DATABASE_URL."""
    if not database_url.strip():
        raise ConfigurationError("ASSISTANT_DATABASE_URL is required for seed")

    reply_text, reply_mode = SandboxEchoReply().generate(text=SEED_USER_TEXT)
    thread = Thread(
        thread_id=SEED_THREAD_ID,
        tenant_id=SEED_TENANT_ID,
        role="customer",
        title=SEED_TITLE,
        created_at=SEED_CREATED_AT,
        updated_at=SEED_CREATED_AT,
        created_by="customer-demo",
    )
    messages = (
        Message(
            message_id=SEED_MESSAGE_ID,
            thread_id=SEED_THREAD_ID,
            tenant_id=SEED_TENANT_ID,
            role="user",
            text=SEED_USER_TEXT,
            evidence_mode=SEED_EVIDENCE_MODE,
            created_at=SEED_CREATED_AT,
            principal_id="customer-demo",
        ),
        Message(
            message_id=SEED_REPLY_ID,
            thread_id=SEED_THREAD_ID,
            tenant_id=SEED_TENANT_ID,
            role="assistant",
            text=reply_text,
            evidence_mode=reply_mode,
            created_at=SEED_CREATED_AT,
            principal_id=None,
        ),
    )

    store = PostgresAssistantStore(build_engine(database_url))
    store.migrate()
    store.upsert_seed_bundle(thread, messages)
    return {
        "status": "PASS",
        "peer": "assistant",
        "tenant_id": SEED_TENANT_ID,
        "thread_id": SEED_THREAD_ID,
        "message_ids": [SEED_MESSAGE_ID, SEED_REPLY_ID],
        "rows": 1 + len(messages),
        "evidence_label": "synthetic-sandbox",
        "evidence_mode": SEED_EVIDENCE_MODE,
    }
