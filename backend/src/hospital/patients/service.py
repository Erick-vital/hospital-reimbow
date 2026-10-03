from uuid import UUID

from sqlalchemy import func, select, true, tuple_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, aliased, selectinload

from hospital.audit.service import record_success
from hospital.authorization.projections import PATIENT_BASIC, PATIENT_DEMOGRAPHICS, patient_projection
from hospital.authorization.service import Actor, authorize
from hospital.core.errors import ApplicationError
from hospital.patients.models import Patient, PatientIdentifier, PatientSearch
from hospital.patients.schemas import PatientCreate, SearchFilters, full_name


def snapshot(patient: Patient) -> dict:
    data = {key: getattr(patient, key) for key in PATIENT_BASIC + PATIENT_DEMOGRAPHICS if key != 'identifiers'}
    data['identifiers'] = [{'system': i.system, 'value': i.value} for i in patient.identifiers]
    return data


def search_patients(session: Session, *, actor: Actor, request_id: UUID, filters: SearchFilters) -> dict:
    authorize(actor, 'patients.search')
    with session.begin():
        criteria = []
        if filters.unidentified:
            criteria.append(False)
        if filters.folio is not None:
            criteria.append(Patient.folio == filters.folio)
        if filters.name is not None:
            name = func.concat_ws(' ', Patient.given_names, Patient.family_name, Patient.second_family_name)
            criteria.append(name.icontains(filters.name, autoescape=True))
        if filters.identifier_system is not None:
            criteria.append(Patient.identifiers.any((PatientIdentifier.system == filters.identifier_system) & (PatientIdentifier.value == filters.identifier_value)))
        count = select(func.count()).select_from(Patient).where(*criteria).subquery()
        page = select(Patient).where(*criteria).order_by(Patient.created_at, Patient.id).limit(filters.limit).offset(filters.offset).subquery()
        patient_alias = aliased(Patient, page)
        rows = session.execute(select(count.c[0], patient_alias).select_from(count).outerjoin(page, true())
                               .options(selectinload(patient_alias.identifiers))
                               .order_by(patient_alias.created_at, patient_alias.id)).all()
        items = [patient_projection(actor, snapshot(p), operation='patients.search') for _, p in rows if p is not None]
        evidence = PatientSearch(actor_id=actor.id, filters=filters.evidence())
        session.add(evidence)
        session.flush()
        record_success(session, actor=actor, action='patients.search', request_id=request_id)
        result = dict(items=items, total=rows[0][0], search_id=evidence.id, limit=filters.limit, offset=filters.offset)
    return result


def check_search(session: Session, actor: Actor, data: PatientCreate):
    evidence = session.scalar(select(PatientSearch).where(PatientSearch.id == data.search_id,
        PatientSearch.actor_id == actor.id, PatientSearch.expires_at > func.clock_timestamp()))
    valid = evidence is not None
    filters = evidence.filters if evidence else {}
    pairs = {(i.system, i.value) for i in data.identifiers}
    name = full_name(data)
    if pairs:
        valid = valid and (filters.get('identifier_system'), filters.get('identifier_value')) in pairs
    elif name:
        valid = valid and filters.get('name', '').lower() == name.lower()
    else:
        valid = valid and filters.get('unidentified') is True
    # Un folio pertenece al registro existente, nunca al alta nueva.
    valid = valid and 'folio' not in filters
    if 'name' in filters:
        valid = valid and filters['name'].lower() == name.lower()
    if 'identifier_system' in filters:
        valid = valid and (filters['identifier_system'], filters['identifier_value']) in pairs
    if filters.get('unidentified'):
        valid = valid and not pairs and not name
    if not valid:
        raise ApplicationError(422, 'SEARCH_REQUIRED', 'Búsqueda previa requerida')


def create_patient(session: Session, *, actor: Actor, request_id: UUID, data: PatientCreate) -> dict:
    operation = 'patients.create_verified' if data.identity_status == 'verified' else 'patients.create'
    authorize(actor, operation)
    try:
        with session.begin():
            check_search(session, actor, data)
            pairs = [(i.system, i.value) for i in data.identifiers]
            if pairs and session.scalar(select(PatientIdentifier.id).where(tuple_(PatientIdentifier.system, PatientIdentifier.value).in_(pairs)).limit(1)):
                raise ApplicationError(409, 'IDENTIFIER_CONFLICT', 'Identificador ya registrado')
            patient = Patient(**data.model_dump(exclude={'search_id', 'identifiers'}), created_by=actor.id,
                              identifiers=[PatientIdentifier(system=i.system, value=i.value) for i in sorted(data.identifiers, key=lambda i: (i.system, i.value))])
            session.add(patient)
            session.flush()
            values = snapshot(patient)
            record_success(session, actor=actor, action='patients.create', resource_id=patient.id, request_id=request_id, new_values=values)
            result = patient_projection(actor, values, operation=operation)
        return result
    except IntegrityError as exc:
        # Sólo la reserva global conocida se convierte en conflicto de negocio.
        if getattr(getattr(exc.orig, 'diag', None), 'constraint_name', None) == 'uq_patient_identifiers_system_value':
            raise ApplicationError(409, 'IDENTIFIER_CONFLICT', 'Identificador ya registrado') from None
        raise


def read_patient(session: Session, *, actor: Actor, request_id: UUID, patient_id: UUID) -> dict:
    authorize(actor, 'patients.read')
    with session.begin():
        patient = session.get(Patient, patient_id)
        if patient is None:
            raise ApplicationError(404, 'RESOURCE_NOT_FOUND', 'Recurso no encontrado')
        result = patient_projection(actor, snapshot(patient))
        record_success(session, actor=actor, action='patients.read', resource_id=patient.id, request_id=request_id)
    return result
