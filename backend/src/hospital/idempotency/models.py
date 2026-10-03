from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column
from hospital.core.database import Base

OPERATIONS = ('v1.patients.create', 'v2.patients.create', 'v1.admissions.create', 'v2.admissions.create')
RESOURCE_CHECK = "(state = 'pending' AND patient_id IS NULL AND admission_id IS NULL) OR (state = 'completed' AND ((operation IN ('v1.patients.create','v2.patients.create') AND patient_id IS NOT NULL AND admission_id IS NULL) OR (operation IN ('v1.admissions.create','v2.admissions.create') AND admission_id IS NOT NULL AND patient_id IS NULL)))"


class IdempotencyRecord(Base):
    __tablename__ = 'idempotency_records'
    __table_args__ = (
        UniqueConstraint('actor_id', 'operation', 'key', name='uq_idempotency_actor_operation_key'),
        CheckConstraint('operation IN (' + ','.join(repr(o) for o in OPERATIONS) + ')', name='operation'),
        CheckConstraint("fingerprint ~ '^[0-9a-f]{64}$'", name='fingerprint'),
        CheckConstraint(RESOURCE_CHECK, name='resource'),
        CheckConstraint("expires_at = created_at + interval '24 hours'", name='window'),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=text('gen_random_uuid()'))
    actor_id: Mapped[UUID] = mapped_column(ForeignKey('institutional_users.id', ondelete='RESTRICT'))
    operation: Mapped[str] = mapped_column(String(40))
    key: Mapped[UUID]
    fingerprint: Mapped[str] = mapped_column(String(64))
    state: Mapped[str] = mapped_column(String(10), server_default='pending')
    patient_id: Mapped[UUID | None] = mapped_column(ForeignKey('patients.id', ondelete='RESTRICT'))
    admission_id: Mapped[UUID | None] = mapped_column(ForeignKey('admissions.id', ondelete='RESTRICT'))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text('transaction_timestamp()'))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("transaction_timestamp() + interval '24 hours'"))
