"""SQLAlchemy tables owned by the case API."""

from __future__ import annotations

from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    UniqueConstraint,
    func,
    text,
)

metadata = MetaData()

cases = Table(
    "cases",
    metadata,
    Column("tenant_id", String(128), primary_key=True),
    Column("case_id", String(128), primary_key=True),
    Column("revision", Integer, nullable=False),
    Column("status", String(64), nullable=False),
    Column("language", String(32), nullable=False),
    Column("intent", String(128), nullable=False),
    Column("evidence_ids_json", Text, nullable=False),
    Column("action_id", String(128)),
    Column("subject_ref", String(256), nullable=False),
    Column("order_reference", String(256), nullable=False),
    Column("original_text", Text, nullable=False),
    Column("channel", String(16), nullable=False),
    Column("owner_queue", String(32)),
    Column("assigned_principal_id", String(128)),
    Column("assessment_id", String(128)),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)

idempotency_keys = Table(
    "idempotency_keys",
    metadata,
    Column("tenant_id", String(128), primary_key=True),
    Column("scope", String(64), primary_key=True),
    Column("idempotency_key", String(256), primary_key=True),
    Column("request_hash", String(128), nullable=False),
    Column("response_json", Text, nullable=False),
    Column("case_id", String(128), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)

messages = Table(
    "case_messages",
    metadata,
    Column("tenant_id", String(128), primary_key=True),
    Column("case_id", String(128), primary_key=True),
    Column("message_id", String(128), primary_key=True),
    Column("text", Text, nullable=False),
    Column("language", String(32), nullable=False),
    Column("author", String(16), nullable=False),
    Column("occurred_at", String(64), nullable=False),
    Column("revision_introduced", Integer, nullable=False),
    Column("sequence", BigInteger, nullable=False),
)

input_snapshots = Table(
    "case_input_snapshots",
    metadata,
    Column("tenant_id", String(128), primary_key=True),
    Column("case_id", String(128), primary_key=True),
    Column("case_revision", Integer, primary_key=True),
    Column("snapshot_json", Text, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)

events = Table(
    "case_events",
    metadata,
    Column("tenant_id", String(128), primary_key=True),
    Column("case_id", String(128), primary_key=True),
    Column("sequence", BigInteger, primary_key=True),
    Column("event_id", String(128), nullable=False),
    Column("case_revision", Integer, nullable=False),
    Column("type", String(64), nullable=False),
    Column("occurred_at", String(64), nullable=False),
    Column("payload_json", Text, nullable=False),
    UniqueConstraint("tenant_id", "case_id", "event_id", name="uq_case_event_id"),
)

result_keys = Table(
    "case_result_keys",
    metadata,
    Column("tenant_id", String(128), primary_key=True),
    Column("case_id", String(128), primary_key=True),
    Column("event_key", String(256), primary_key=True),
    Column("payload_hash", String(128), nullable=False),
    Column("case_snapshot_json", Text, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)

workflow_outbox = Table(
    "workflow_outbox",
    metadata,
    Column("id", String(128), primary_key=True),
    Column("tenant_id", String(128), nullable=False),
    Column("job_key", String(256), nullable=False),
    Column("payload_json", Text, nullable=False),
    Column("status", String(32), nullable=False, server_default=text("'PENDING'")),
    Column("detail", Text, nullable=False, server_default=text("''")),
    # CLAIMED: lease expiry. PENDING: earliest next attempt (NULL = now).
    Column("lease_expires_at", DateTime(timezone=True), nullable=True),
    Column("attempts", Integer, nullable=False, server_default=text("0")),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    UniqueConstraint("tenant_id", "job_key", name="uq_workflow_job_key"),
)

action_case_index = Table(
    "action_case_index",
    metadata,
    Column("tenant_id", String(128), primary_key=True),
    Column("action_id", String(128), primary_key=True),
    Column("case_id", String(128), nullable=False),
)
