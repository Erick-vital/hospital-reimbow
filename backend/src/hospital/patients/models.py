from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Index, Sequence, String, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from hospital.core.database import Base

patient_folio_sequence = Sequence('patient_folio_seq', metadata=Base.metadata)


class Patient(Base):
    __tablename__ = 'patients'
    __table_args__ = (
        CheckConstraint("identity_status IN ('provisional', 'verified')", name='identity_status'),
        CheckConstraint("identity_status <> 'verified' OR given_names IS NOT NULL", name='verified_name'),
        CheckConstraint("folio ~ '^PAC-[0-9]{12,}$'", name='folio_format'),
        CheckConstraint("(given_names IS NULL OR length(trim(given_names)) > 0) AND (family_name IS NULL OR length(trim(family_name)) > 0) AND (second_family_name IS NULL OR length(trim(second_family_name)) > 0)", name='names_not_empty'),
        CheckConstraint("birth_date IS NULL OR birth_date <= (CURRENT_TIMESTAMP AT TIME ZONE 'UTC')::date", name='birth_date'),
        Index('ix_patients_created_at_id', 'created_at', 'id'),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4, server_default=text('gen_random_uuid()'))
    folio: Mapped[str] = mapped_column(String(32), unique=True, server_default=text('next_patient_folio()'))
    identity_status: Mapped[str] = mapped_column(String(20))
    given_names: Mapped[str | None] = mapped_column(String(100))
    family_name: Mapped[str | None] = mapped_column(String(100))
    second_family_name: Mapped[str | None] = mapped_column(String(100))
    birth_date: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.clock_timestamp())
    created_by: Mapped[UUID] = mapped_column(ForeignKey('institutional_users.id', ondelete='RESTRICT'))
    identifiers: Mapped[list['PatientIdentifier']] = relationship(order_by='PatientIdentifier.system, PatientIdentifier.value')


class PatientIdentifier(Base):
    __tablename__ = 'patient_identifiers'
    __table_args__ = (
        UniqueConstraint('system', 'value', name='uq_patient_identifiers_system_value'),
        CheckConstraint("(system = 'CURP' AND value ~ '^[A-Z0-9]{18}$') OR (system = 'TEST' AND value ~ '^[A-Z0-9_-]{1,64}$')", name='identifier_format'),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4, server_default=text('gen_random_uuid()'))
    patient_id: Mapped[UUID] = mapped_column(ForeignKey('patients.id', ondelete='RESTRICT'), index=True)
    system: Mapped[str] = mapped_column(String(10))
    value: Mapped[str] = mapped_column(String(64))


class PatientSearch(Base):
    __tablename__ = 'patient_searches'
    __table_args__ = (
        CheckConstraint("jsonb_typeof(filters) = 'object'", name='filters_object'),
        CheckConstraint('expires_at > created_at', name='expiry'),
        Index('ix_patient_searches_expires_at', 'expires_at'),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4, server_default=text('gen_random_uuid()'))
    actor_id: Mapped[UUID] = mapped_column(ForeignKey('institutional_users.id', ondelete='RESTRICT'))
    filters: Mapped[dict] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.clock_timestamp())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("(clock_timestamp() + '00:15:00'::interval)"))
