from uuid import UUID

from sqlalchemy import func, select, true
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, aliased

from hospital.idempotency.service import execute_create
from hospital.admissions.models import Admission
from hospital.admissions.schemas import AdmissionCreate
from hospital.audit.service import record_success
from hospital.authorization.projections import ADMISSION_FIELDS, admission_projection
from hospital.authorization.service import Actor, authorize
from hospital.core.errors import ApplicationError
from hospital.patients.models import Patient


def snapshot(admission: Admission) -> dict:
    return {field: getattr(admission, field) for field in ADMISSION_FIELDS}


def require_patient(session: Session, patient_id: UUID) -> None:
    # Consultar sólo identidad interna; los episodios no entregan demografía.
    if session.scalar(select(Patient.id).where(Patient.id == patient_id)) is None:
        raise ApplicationError(404, 'RESOURCE_NOT_FOUND', 'Recurso no encontrado')


def create_admission(session: Session, *, actor: Actor, request_id: UUID, data: AdmissionCreate,
                     idempotency_key=None, idempotency_metadata=None) -> dict:
    authorize(actor, 'admissions.create')
    def create():
        admission = insert_admission(session, actor, data)
        record_success(session, actor=actor, action='admissions.create', request_id=request_id,
                       resource_id=admission.id, new_values=snapshot(admission))
        return admission
    try:
        return execute_create(session, actor=actor, request_id=request_id, data=data,
            operation='v1.admissions.create', key=idempotency_key, metadata=idempotency_metadata,
            create=create, project=lambda a: admission_projection(actor, snapshot(a), operation='admissions.create'), model=Admission)
    except IntegrityError as exc:
        if getattr(getattr(exc.orig, 'diag', None), 'constraint_name', None) == 'fk_admissions_patient_id_patients':
            raise ApplicationError(404, 'RESOURCE_NOT_FOUND', 'Recurso no encontrado') from None
        raise


def insert_admission(session: Session, actor: Actor, data: AdmissionCreate) -> Admission:
    require_patient(session, data.patient_id)
    admission = Admission(patient_id=data.patient_id, type=data.type, created_by=actor.id)
    session.add(admission)
    session.flush()
    return admission


def read_admission(session: Session, *, actor: Actor, request_id: UUID, admission_id: UUID, project=None) -> dict:
    authorize(actor, 'admissions.read')
    with session.begin():
        admission = session.get(Admission, admission_id)
        if admission is None:
            raise ApplicationError(404, 'RESOURCE_NOT_FOUND', 'Recurso no encontrado')
        result = project(session, actor, admission, 'admissions.read') if project else admission_projection(actor, snapshot(admission))
        record_success(session, actor=actor, action='admissions.read', request_id=request_id, resource_id=admission.id)
    return result


def list_admissions(session: Session, *, actor: Actor, request_id: UUID, patient_id: UUID,
                    limit: int = 20, offset: int = 0, project=None) -> dict:
    authorize(actor, 'admissions.list')
    with session.begin():
        require_patient(session, patient_id)
        criterion = Admission.patient_id == patient_id
        count = select(func.count()).select_from(Admission).where(criterion).subquery()
        page = select(Admission).where(criterion).order_by(Admission.created_at, Admission.id).limit(limit).offset(offset).subquery()
        admission_alias = aliased(Admission, page)
        rows = session.execute(select(count.c[0], admission_alias).select_from(count).outerjoin(page, true())
                               .order_by(admission_alias.created_at, admission_alias.id)).all()
        result = {'items': [(project(session, actor, a, 'admissions.list') if project else admission_projection(actor, snapshot(a), operation='admissions.list')) for _, a in rows if a is not None],
                  'total': rows[0][0], 'limit': limit, 'offset': offset}
        record_success(session, actor=actor, action='admissions.list', request_id=request_id)
    return result
