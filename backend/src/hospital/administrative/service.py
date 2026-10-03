from sqlalchemy import func, select, true
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import aliased

from hospital.administrative.models import AdmissionIntake, PatientCollectionItem, PatientProfile, Service, Site, Verification, VerificationEvidence
from hospital.administrative.projections import admission_v2_projection, patient_v2_projection
from hospital.admissions.service import insert_admission, snapshot as admission_snapshot
from hospital.audit.service import record_success
from hospital.authorization.service import authorize
from hospital.core.errors import ApplicationError
from hospital.patients.service import insert_patient, snapshot as patient_snapshot


def create_patient_v2(session, *, actor, request_id, data):
    operation = 'patients.create_verified' if data.identity_status == 'verified' else 'patients.create'
    authorize(actor, operation)
    try:
        with session.begin():
            patient = insert_patient(session, actor, data)
            profile = data.administrative_profile.model_dump(mode='json')
            collections = {k: profile.pop(k) for k in ('phones', 'addresses', 'emergency_contacts')}
            profile.update(collection_states={k: v['state'] for k, v in collections.items()},
                           identity_field_states=data.identity_field_states.model_dump(),
                           unidentified_description=data.unidentified_description.model_dump(mode='json'))
            session.add(PatientProfile(patient_id=patient.id, is_unidentified=data.is_unidentified, data=profile))
            session.flush()
            for kind, collection in collections.items():
                for position, item in enumerate(collection['value'] or []):
                    session.add(PatientCollectionItem(patient_id=patient.id, kind=kind, position=position, data=item))
            if data.verification:
                session.add(Verification(patient_id=patient.id, verified_by=actor.id))
                session.flush()
                for evidence in data.verification:
                    if evidence.field == 'full_name':
                        snapshot = {k: getattr(data, k) for k in ('given_names', 'family_name', 'second_family_name')}
                    elif evidence.field == 'birth_date':
                        snapshot = {'birth_date': data.birth_date.isoformat()}
                    else:
                        snapshot = {'CURP': next(i.value for i in data.identifiers if i.system == 'CURP')}
                    session.add(VerificationEvidence(patient_id=patient.id, snapshot=snapshot, **evidence.model_dump()))
            session.flush()
            # Auditoría conserva la lista explícita V1; evidencia ampliada vive en
            # tablas protegidas, no en logs ni metadatos arbitrarios.
            record_success(session, actor=actor, request_id=request_id, action='patients.create',
                           resource_id=patient.id, new_values=patient_snapshot(patient))
            result = patient_v2_projection(session, actor, patient, operation)
        return result
    except IntegrityError as exc:
        if getattr(getattr(exc.orig, 'diag', None), 'constraint_name', None) == 'uq_patient_identifiers_system_value':
            raise ApplicationError(409, 'IDENTIFIER_CONFLICT', 'Identificador ya registrado') from None
        raise


def validate_catalogs(session, intake):
    if intake.site_id.value is not None:
        site = session.scalar(select(Site).where(Site.id == intake.site_id.value).with_for_update(read=True))
        if site is None or not site.active:
            raise ApplicationError(422, 'VALIDATION_ERROR', 'Sede no disponible')
    if intake.service_id.value is not None:
        service = session.scalar(select(Service).where(Service.id == intake.service_id.value).with_for_update(read=True))
        if service is None or not service.active or service.site_id != intake.site_id.value:
            raise ApplicationError(422, 'VALIDATION_ERROR', 'Servicio no disponible para la sede')


def create_admission_v2(session, *, actor, request_id, data):
    authorize(actor, 'admissions.create')
    with session.begin():
        validate_catalogs(session, data.intake)
        admission = insert_admission(session, actor, data)
        session.add(AdmissionIntake(admission_id=admission.id, data=data.intake.model_dump(mode='json'),
                                   admitted_at=data.intake.admitted_at.value, site_id=data.intake.site_id.value,
                                   service_id=data.intake.service_id.value))
        session.flush()
        record_success(session, actor=actor, request_id=request_id, action='admissions.create',
                       resource_id=admission.id, new_values=admission_snapshot(admission))
        result = admission_v2_projection(session, actor, admission, 'admissions.create')
    return result


def list_catalog(session, *, actor, request_id, kind, site_id=None, limit=20, offset=0):
    authorize(actor, 'catalogs.read')
    with session.begin():
        model = Site if kind == 'sites' else Service
        criteria = [model.active.is_(True)]
        if kind == 'services':
            site = session.get(Site, site_id)
            if site is None or not site.active:
                raise ApplicationError(404, 'RESOURCE_NOT_FOUND', 'Sede no encontrada')
            criteria.append(Service.site_id == site_id)
        count = select(func.count()).select_from(model).where(*criteria).subquery()
        page = select(model).where(*criteria).order_by(model.code, model.id).limit(limit).offset(offset).subquery()
        item = aliased(model, page)
        rows = session.execute(select(count.c[0], item).select_from(count).outerjoin(page, true()).order_by(item.code, item.id)).all()
        fields = ('id', 'code', 'name') + (('site_id',) if kind == 'services' else ())
        result = dict(items=[{f: getattr(row, f) for f in fields} for _, row in rows if row is not None],
                      total=rows[0][0], limit=limit, offset=offset)
        record_success(session, actor=actor, request_id=request_id, action='catalogs.read')
    return result
