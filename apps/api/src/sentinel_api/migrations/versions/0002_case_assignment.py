"""case assignment for operator claim

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-14
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("cases", sa.Column("assigned_principal_id", sa.String(128), nullable=True))


def downgrade() -> None:
    op.drop_column("cases", "assigned_principal_id")
