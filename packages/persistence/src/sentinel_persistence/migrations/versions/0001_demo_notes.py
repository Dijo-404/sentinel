"""Non-financial tenant key / RLS example owned solely by this demonstration."""

import sqlalchemy as sa
from alembic import context, op

from sentinel_persistence.postgres import apply_tenant_policy

revision = "0001_demo_notes"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    service = context.config.attributes["service"]
    schema = service.schema
    op.create_table(
        "demo_records",
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("label", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("tenant_id", "id", name="pk_demo_records"),
        sa.CheckConstraint("tenant_id <> '' AND id <> ''", name="ck_demo_record_identity"),
        schema=schema,
    )
    op.create_table(
        "demo_notes",
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("record_id", sa.Text(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("tenant_id", "id", name="pk_demo_notes"),
        sa.ForeignKeyConstraint(
            ["tenant_id", "record_id"],
            [f"{schema}.demo_records.tenant_id", f"{schema}.demo_records.id"],
            name="fk_demo_note_tenant_record",
        ),
        schema=schema,
    )
    connection = op.get_bind()
    connection.exec_driver_sql(f'REVOKE ALL ON SCHEMA "{schema}" FROM PUBLIC')
    connection.exec_driver_sql(f'GRANT USAGE ON SCHEMA "{schema}" TO "{service.runtime_role}"')
    for table in ("demo_records", "demo_notes"):
        apply_tenant_policy(connection, service, table)
    connection.exec_driver_sql(
        f"COMMENT ON TABLE \"{schema}\".demo_records IS 'persistence-kit.v1:0001_demo_notes'"
    )


def downgrade() -> None:
    schema = context.config.attributes["service"].schema
    op.drop_table("demo_notes", schema=schema)
    op.drop_table("demo_records", schema=schema)
