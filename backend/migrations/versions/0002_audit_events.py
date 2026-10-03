"""Auditoría transaccional V1.

Revision ID: 0002
Revises: 0001
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "audit_events",
        sa.Column("id", sa.Uuid(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("actor_id", sa.Uuid(), nullable=True),
        sa.Column("action", sa.String(40), nullable=False),
        sa.Column("resource_type", sa.String(20), nullable=True),
        sa.Column("resource_id", sa.Uuid(), nullable=True),
        sa.Column("result", sa.String(10), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("clock_timestamp()")),
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audit_events")),
        sa.ForeignKeyConstraint(["actor_id"], ["institutional_users.id"], ondelete="RESTRICT", name=op.f("fk_audit_events_actor_id_institutional_users")),
        sa.CheckConstraint("action IN ('patients.search','patients.create','patients.read','admissions.create','admissions.read','admissions.list','audit.read','identity.read')", name=op.f("ck_audit_events_action")),
        sa.CheckConstraint("result IN ('success','denied')", name=op.f("ck_audit_events_result")),
        sa.CheckConstraint("actor_id IS NOT NULL OR result = 'denied'", name=op.f("ck_audit_events_success_actor")),
        sa.CheckConstraint("resource_type IS NULL OR resource_type IN ('patients','admissions','audit','identity')", name=op.f("ck_audit_events_resource_type")),
        sa.CheckConstraint("jsonb_typeof(metadata) = 'object'", name=op.f("ck_audit_events_metadata_object")),
        sa.CheckConstraint("result <> 'denied' OR (resource_id IS NULL AND metadata IN ('{\"code\":\"IDENTITY_REQUIRED\"}'::jsonb, '{\"code\":\"PERMISSION_DENIED\"}'::jsonb))", name=op.f("ck_audit_events_denied_minimal")),
    )
    op.create_index("ix_audit_events_created_at_id", "audit_events", ["created_at", "id"])
    op.create_index("ix_audit_events_resource_id", "audit_events", ["resource_id"])
    op.create_index("ix_audit_events_action", "audit_events", ["action"])


def downgrade() -> None:
    op.drop_table("audit_events")
