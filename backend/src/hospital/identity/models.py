from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, String, UniqueConstraint, func, text
from sqlalchemy.orm import Mapped, mapped_column

from hospital.core.database import Base


class User(Base):
    __tablename__ = "institutional_users"
    __table_args__ = (
        UniqueConstraint("provider", "subject"),
        CheckConstraint("status IN ('active', 'inactive')", name="status"),
        CheckConstraint("length(trim(actor_key)) > 0 AND length(trim(provider)) > 0 AND length(trim(subject)) > 0", name="identity_not_empty"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4, server_default=text("gen_random_uuid()"))
    actor_key: Mapped[str] = mapped_column(String(100), unique=True)
    provider: Mapped[str] = mapped_column(String(100))
    subject: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(20), server_default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
