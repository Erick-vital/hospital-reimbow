from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Sequence, String, func, text
from sqlalchemy.orm import Mapped, mapped_column

from hospital.core.database import Base

admission_folio_sequence = Sequence('admission_folio_seq', metadata=Base.metadata)


class Admission(Base):
    __tablename__ = 'admissions'
    __table_args__ = (
        CheckConstraint("type IN ('emergency', 'outpatient', 'inpatient')", name='type'),
        CheckConstraint("status = 'open'", name='status'),
        CheckConstraint("folio ~ '^EPI-[0-9]{12,}$'", name='folio_format'),
        Index('ix_admissions_patient_id_created_at_id', 'patient_id', 'created_at', 'id'),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4, server_default=text('gen_random_uuid()'))
    folio: Mapped[str] = mapped_column(String(32), unique=True, server_default=text('next_admission_folio()'))
    patient_id: Mapped[UUID] = mapped_column(ForeignKey('patients.id', ondelete='RESTRICT'))
    type: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), server_default='open')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.clock_timestamp())
    created_by: Mapped[UUID] = mapped_column(ForeignKey('institutional_users.id', ondelete='RESTRICT'))
