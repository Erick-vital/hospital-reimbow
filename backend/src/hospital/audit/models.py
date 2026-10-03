from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from hospital.core.database import Base

ACTIONS = (
    "patients.search", "patients.create", "patients.read", "admissions.create",
    "admissions.read", "admissions.list", "audit.read", "identity.read", "catalogs.read", "patients.replay", "admissions.replay",
)


class AuditEvent(Base):
    __tablename__ = "audit_events"
    __table_args__ = (
        CheckConstraint("action IN (" + ",".join(repr(a) for a in ACTIONS) + ")", name="action"),
        CheckConstraint("result IN ('success','denied')", name="result"),
        CheckConstraint("actor_id IS NOT NULL OR result = 'denied'", name="success_actor"),
        CheckConstraint("resource_type IS NULL OR resource_type IN ('patients','admissions','audit','identity','catalogs')", name="resource_type"),
        CheckConstraint("jsonb_typeof(metadata) = 'object'", name="metadata_object"),
        CheckConstraint("result <> 'denied' OR (resource_id IS NULL AND metadata IN ('{\"code\":\"IDENTITY_REQUIRED\"}'::jsonb, '{\"code\":\"PERMISSION_DENIED\"}'::jsonb))", name="denied_minimal"),
        Index("ix_audit_events_created_at_id", "created_at", "id"),
        Index("ix_audit_events_resource_id", "resource_id"),
        Index("ix_audit_events_action", "action"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4, server_default=text("gen_random_uuid()"))
    actor_id: Mapped[UUID | None] = mapped_column(ForeignKey("institutional_users.id", ondelete="RESTRICT"))
    action: Mapped[str] = mapped_column(String(40))
    resource_type: Mapped[str | None] = mapped_column(String(20))
    resource_id: Mapped[UUID | None]
    result: Mapped[str] = mapped_column(String(10))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("clock_timestamp()"))
    request_id: Mapped[UUID]
    event_metadata: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, server_default=text("'{}'::jsonb"))
