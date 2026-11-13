"""case api tables

Revision ID: 0001
Revises:
Create Date: 2026-11-13
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cases",
        sa.Column("tenant_id", sa.String(128), primary_key=True),
        sa.Column("case_id", sa.String(128), primary_key=True),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(64), nullable=False),
        sa.Column("language", sa.String(32), nullable=False),
        sa.Column("intent", sa.String(128), nullable=False),
        sa.Column("evidence_ids_json", sa.Text(), nullable=False),
        sa.Column("action_id", sa.String(128)),
        sa.Column("subject_ref", sa.String(256), nullable=False),
        sa.Column("order_reference", sa.String(256), nullable=False),
        sa.Column("original_text", sa.Text(), nullable=False),
        sa.Column("channel", sa.String(16), nullable=False),
        sa.Column("owner_queue", sa.String(32)),
        sa.Column("assessment_id", sa.String(128)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "idempotency_keys",
        sa.Column("tenant_id", sa.String(128), primary_key=True),
        sa.Column("scope", sa.String(64), primary_key=True),
        sa.Column("idempotency_key", sa.String(256), primary_key=True),
        sa.Column("request_hash", sa.String(128), nullable=False),
        sa.Column("response_json", sa.Text(), nullable=False),
        sa.Column("case_id", sa.String(128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "case_messages",
        sa.Column("tenant_id", sa.String(128), primary_key=True),
        sa.Column("case_id", sa.String(128), primary_key=True),
        sa.Column("message_id", sa.String(128), primary_key=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("language", sa.String(32), nullable=False),
        sa.Column("author", sa.String(16), nullable=False),
        sa.Column("occurred_at", sa.String(64), nullable=False),
        sa.Column("revision_introduced", sa.Integer(), nullable=False),
        sa.Column("sequence", sa.BigInteger(), nullable=False),
    )
    op.create_table(
        "case_input_snapshots",
        sa.Column("tenant_id", sa.String(128), primary_key=True),
        sa.Column("case_id", sa.String(128), primary_key=True),
        sa.Column("case_revision", sa.Integer(), primary_key=True),
        sa.Column("snapshot_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "case_events",
        sa.Column("tenant_id", sa.String(128), primary_key=True),
        sa.Column("case_id", sa.String(128), primary_key=True),
        sa.Column("sequence", sa.BigInteger(), primary_key=True),
        sa.Column("event_id", sa.String(128), nullable=False),
        sa.Column("case_revision", sa.Integer(), nullable=False),
        sa.Column("type", sa.String(64), nullable=False),
        sa.Column("occurred_at", sa.String(64), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.UniqueConstraint("tenant_id", "case_id", "event_id", name="uq_case_event_id"),
    )
    op.create_table(
        "case_result_keys",
        sa.Column("tenant_id", sa.String(128), primary_key=True),
        sa.Column("case_id", sa.String(128), primary_key=True),
        sa.Column("event_key", sa.String(256), primary_key=True),
        sa.Column("payload_hash", sa.String(128), nullable=False),
        sa.Column("case_snapshot_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "workflow_outbox",
        sa.Column("id", sa.String(128), primary_key=True),
        sa.Column("tenant_id", sa.String(128), nullable=False),
        sa.Column("job_key", sa.String(256), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="PENDING"),
        sa.Column("detail", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("tenant_id", "job_key", name="uq_workflow_job_key"),
    )
    op.create_table(
        "action_case_index",
        sa.Column("tenant_id", sa.String(128), primary_key=True),
        sa.Column("action_id", sa.String(128), primary_key=True),
        sa.Column("case_id", sa.String(128), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("action_case_index")
    op.drop_table("workflow_outbox")
    op.drop_table("case_result_keys")
    op.drop_table("case_events")
    op.drop_table("case_input_snapshots")
    op.drop_table("case_messages")
    op.drop_table("idempotency_keys")
    op.drop_table("cases")
