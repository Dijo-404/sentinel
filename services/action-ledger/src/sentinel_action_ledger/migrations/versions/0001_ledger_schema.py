"""Authoritative ledger tables: approvals, eligibility, reservations, actions, outbox, audit.

Revision ID: 0001_ledger_schema
Revises:
Create Date: 2026-11-13
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0001_ledger_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "actions",
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("action_id", sa.Text(), nullable=False),
        sa.Column("operation_key", sa.Text(), nullable=False),
        sa.Column("provider_ref", sa.Text(), nullable=False),
        sa.Column("payload", JSONB(), nullable=False),
        sa.Column("action_digest", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("amount_minor", sa.BigInteger(), nullable=False),
        sa.Column("currency", sa.Text(), nullable=False),
        sa.Column("transaction_ref", sa.Text(), nullable=False),
        sa.Column("case_id", sa.Text(), nullable=False),
        sa.Column("case_revision", sa.Integer(), nullable=False),
        sa.Column("policy_version", sa.Text(), nullable=False),
        sa.Column("approval_id", sa.Text(), nullable=True),
        sa.Column("lease_id", sa.Text(), nullable=True),
        sa.Column("lease_expires_at", sa.Text(), nullable=True),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("tenant_id", "action_id"),
        sa.UniqueConstraint("tenant_id", "operation_key", name="uq_actions_operation"),
        sa.UniqueConstraint("tenant_id", "provider_ref", name="uq_actions_provider_ref"),
        sa.CheckConstraint("amount_minor > 0", name="ck_actions_amount_positive"),
        sa.CheckConstraint("case_revision > 0", name="ck_actions_revision_positive"),
    )
    op.create_table(
        "approvals",
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("approval_id", sa.Text(), nullable=False),
        sa.Column("action_id", sa.Text(), nullable=False),
        sa.Column("action_digest", sa.Text(), nullable=False),
        sa.Column("case_revision", sa.Integer(), nullable=False),
        sa.Column("policy_version", sa.Text(), nullable=False),
        sa.Column("decision", sa.Text(), nullable=False),
        sa.Column("reviewer_id", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.Text(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("tenant_id", "approval_id"),
        sa.ForeignKeyConstraint(
            ["tenant_id", "action_id"],
            ["actions.tenant_id", "actions.action_id"],
            name="fk_approvals_action",
        ),
        sa.UniqueConstraint("tenant_id", "action_id", name="uq_approvals_action"),
        sa.CheckConstraint("decision IN ('APPROVE', 'REJECT')", name="ck_approvals_decision"),
    )
    op.create_table(
        "payment_reservations",
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("transaction_ref", sa.Text(), nullable=False),
        sa.Column("merchant_ref", sa.Text(), nullable=False),
        sa.Column("captured_minor", sa.BigInteger(), nullable=False),
        sa.Column("reserved_minor", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("pending_minor", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("refunded_minor", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("currency", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("tenant_id", "transaction_ref"),
        sa.CheckConstraint("captured_minor >= 0", name="ck_pay_captured"),
        sa.CheckConstraint("reserved_minor >= 0", name="ck_pay_reserved"),
        sa.CheckConstraint("pending_minor >= 0", name="ck_pay_pending"),
        sa.CheckConstraint("refunded_minor >= 0", name="ck_pay_refunded"),
        sa.CheckConstraint(
            "reserved_minor + pending_minor + refunded_minor <= captured_minor",
            name="ck_pay_invariant",
        ),
    )
    op.create_table(
        "eligibility_snapshots",
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("transaction_ref", sa.Text(), nullable=False),
        sa.Column("case_id", sa.Text(), nullable=False),
        sa.Column("subject_ref", sa.Text(), nullable=False),
        sa.Column("captured_minor", sa.BigInteger(), nullable=False),
        sa.Column("currency", sa.Text(), nullable=False),
        sa.Column("payment_status", sa.Text(), nullable=False),
        sa.Column("observed_at", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.Text(), nullable=False),
        sa.Column("evidence_digest", sa.Text(), nullable=False),
        sa.Column("external_refunded_minor", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("external_pending_minor", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("tenant_id", "transaction_ref"),
    )
    op.create_table(
        "outbox",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("action_id", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("available_at", sa.Text(), nullable=False),
        sa.Column("payload", JSONB(), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("lease_id", sa.Text(), nullable=True),
        sa.Column("lease_expires_at", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["tenant_id", "action_id"],
            ["actions.tenant_id", "actions.action_id"],
            name="fk_outbox_action",
        ),
        sa.UniqueConstraint("tenant_id", "action_id", name="uq_outbox_action"),
    )
    op.create_index(
        "ix_outbox_claim",
        "outbox",
        ["tenant_id", "status", "available_at"],
    )
    op.create_table(
        "financial_audit",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("action_id", sa.Text(), nullable=False),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("actor_id", sa.Text(), nullable=False),
        sa.Column("detail", JSONB(), nullable=False),
        sa.Column("occurred_at", sa.Text(), nullable=False),
    )
    op.create_index(
        "ix_financial_audit_action",
        "financial_audit",
        ["tenant_id", "action_id", "occurred_at"],
    )
    op.create_table(
        "outcome_events",
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("action_id", sa.Text(), nullable=False),
        sa.Column("event_key", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("reason_code", sa.Text(), nullable=False),
        sa.Column("evidence_ids", JSONB(), nullable=False),
        sa.Column("occurred_at", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("tenant_id", "action_id", "event_key"),
        sa.ForeignKeyConstraint(
            ["tenant_id", "action_id"],
            ["actions.tenant_id", "actions.action_id"],
            name="fk_outcome_action",
        ),
    )


def downgrade() -> None:
    op.drop_table("outcome_events")
    op.drop_index("ix_financial_audit_action", table_name="financial_audit")
    op.drop_table("financial_audit")
    op.drop_index("ix_outbox_claim", table_name="outbox")
    op.drop_table("outbox")
    op.drop_table("eligibility_snapshots")
    op.drop_table("payment_reservations")
    op.drop_table("approvals")
    op.drop_table("actions")
