from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, ForeignKeyConstraint, Integer, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from hospital.core.database import Base


class PatientProfile(Base):
    __tablename__ = 'patient_administrative_profiles'
    __table_args__ = (CheckConstraint('v2_profile_valid(data) IS TRUE', name='profile_valid'),)
    patient_id: Mapped[UUID] = mapped_column(ForeignKey('patients.id', ondelete='RESTRICT'), primary_key=True)
    is_unidentified: Mapped[bool] = mapped_column(Boolean)
    data: Mapped[dict] = mapped_column(JSONB)


class PatientCollectionItem(Base):
    __tablename__ = 'patient_administrative_items'
    __table_args__ = (
        CheckConstraint("kind IN ('phones','addresses','emergency_contacts')", name='kind'),
        CheckConstraint('position BETWEEN 0 AND 9', name='position'),
        CheckConstraint('v2_item_valid(kind, data) IS TRUE', name='item_valid'),
    )
    patient_id: Mapped[UUID] = mapped_column(ForeignKey('patient_administrative_profiles.patient_id', ondelete='RESTRICT'), primary_key=True)
    kind: Mapped[str] = mapped_column(String(30), primary_key=True)
    position: Mapped[int] = mapped_column(Integer, primary_key=True)
    data: Mapped[dict] = mapped_column(JSONB)


class Verification(Base):
    __tablename__ = 'patient_identity_verifications'
    patient_id: Mapped[UUID] = mapped_column(ForeignKey('patient_administrative_profiles.patient_id', ondelete='RESTRICT'), primary_key=True)
    verified_by: Mapped[UUID] = mapped_column(ForeignKey('institutional_users.id', ondelete='RESTRICT'))
    verified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text('clock_timestamp()'))


class VerificationEvidence(Base):
    __tablename__ = 'patient_verification_evidence'
    __table_args__ = (
        CheckConstraint("field IN ('full_name','birth_date','CURP')", name='field'),
        CheckConstraint("source_kind IN ('official_document','institutional_document')", name='source_kind'),
        CheckConstraint('length(trim(source_reference)) BETWEEN 1 AND 200', name='source_reference'),
        CheckConstraint("jsonb_typeof(snapshot) = 'object'", name='snapshot'),
    )
    patient_id: Mapped[UUID] = mapped_column(ForeignKey('patient_identity_verifications.patient_id', ondelete='RESTRICT'), primary_key=True)
    field: Mapped[str] = mapped_column(String(20), primary_key=True)
    source_kind: Mapped[str] = mapped_column(String(30))
    source_reference: Mapped[str] = mapped_column(String(200))
    snapshot: Mapped[dict] = mapped_column(JSONB)


class Site(Base):
    __tablename__ = 'admission_sites'
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4, server_default=text('gen_random_uuid()'))
    code: Mapped[str] = mapped_column(String(50), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    active: Mapped[bool] = mapped_column(Boolean, server_default=text('true'))


class Service(Base):
    __tablename__ = 'admission_services'
    __table_args__ = (UniqueConstraint('site_id', 'code'), UniqueConstraint('site_id', 'id', name='uq_admission_services_site_id_id'))
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4, server_default=text('gen_random_uuid()'))
    site_id: Mapped[UUID] = mapped_column(ForeignKey('admission_sites.id', ondelete='RESTRICT'), index=True)
    code: Mapped[str] = mapped_column(String(50))
    name: Mapped[str] = mapped_column(String(200))
    active: Mapped[bool] = mapped_column(Boolean, server_default=text('true'))


class AdmissionIntake(Base):
    __tablename__ = 'admission_intakes'
    __table_args__ = (
        ForeignKeyConstraint(['site_id', 'service_id'], ['admission_services.site_id', 'admission_services.id'], ondelete='RESTRICT', name='fk_admission_intakes_site_service'),
        CheckConstraint('v2_intake_valid(data) IS TRUE', name='intake_valid'),
        CheckConstraint("(data->'site_id'->>'value')::uuid IS NOT DISTINCT FROM site_id AND (data->'service_id'->>'value')::uuid IS NOT DISTINCT FROM service_id", name='catalog_values'),
        CheckConstraint("service_id IS NULL OR site_id IS NOT NULL", name='service_site'),
        CheckConstraint("admitted_at IS NULL OR admitted_at <= clock_timestamp()", name='past_admission'),
    )
    admission_id: Mapped[UUID] = mapped_column(ForeignKey('admissions.id', ondelete='RESTRICT'), primary_key=True)
    data: Mapped[dict] = mapped_column(JSONB)
    admitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    site_id: Mapped[UUID | None] = mapped_column(ForeignKey('admission_sites.id', ondelete='RESTRICT'))
    service_id: Mapped[UUID | None] = mapped_column(ForeignKey('admission_services.id', ondelete='RESTRICT'))
