from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, ForeignKey, String, text
from sqlalchemy.orm import Mapped, mapped_column

from hospital.core.database import Base


class Role(Base):
    __tablename__ = "roles"
    __table_args__ = (CheckConstraint("length(trim(code)) > 0", name="code_not_empty"),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4, server_default=text("gen_random_uuid()"))
    code: Mapped[str] = mapped_column(String(100), unique=True)


class Permission(Base):
    __tablename__ = "permissions"
    __table_args__ = (CheckConstraint("length(trim(code)) > 0", name="code_not_empty"),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4, server_default=text("gen_random_uuid()"))
    code: Mapped[str] = mapped_column(String(100), unique=True)


class UserRole(Base):
    __tablename__ = "user_roles"
    user_id: Mapped[UUID] = mapped_column(ForeignKey("institutional_users.id", ondelete="RESTRICT"), primary_key=True)
    role_id: Mapped[UUID] = mapped_column(ForeignKey("roles.id", ondelete="RESTRICT"), primary_key=True)


class RolePermission(Base):
    __tablename__ = "role_permissions"
    role_id: Mapped[UUID] = mapped_column(ForeignKey("roles.id", ondelete="RESTRICT"), primary_key=True)
    permission_id: Mapped[UUID] = mapped_column(ForeignKey("permissions.id", ondelete="RESTRICT"), primary_key=True)
