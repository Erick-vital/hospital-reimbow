from sqlalchemy import func, select, true
from sqlalchemy.orm import aliased

from hospital.administrative.models import AdmissionIntake, Service, Site, Verification
from hospital.admissions.models import Admission
from hospital.audit.service import record_success
from hospital.authorization.service import authorize
from hospital.clinical.projections import episode_projection, patient_projection
from hospital.core.errors import ApplicationError
from hospital.patients.models import Patient


def missing():
    raise ApplicationError(404, 'RESOURCE_NOT_FOUND', 'Recurso no encontrado')


def validate_filters(session, site_id, service_id):
    if service_id is not None and site_id is None:
        raise ApplicationError(422, 'VALIDATION_ERROR', 'El filtro servicio requiere sede')
    if site_id is not None:
        site = session.get(Site, site_id)
        if site is None or not site.active:
            missing()
    if service_id is not None:
        service = session.get(Service, service_id)
        if service is None or not service.active:
            missing()
        if service.site_id != site_id:
            raise ApplicationError(422, 'VALIDATION_ERROR', 'Servicio incompatible con sede')


def attention_rows(session, criteria, limit, offset):
    # Total/página/proyección comparten una sentencia y snapshot PostgreSQL.
    base = select(Admission).outerjoin(AdmissionIntake, AdmissionIntake.admission_id == Admission.id).where(*criteria)
    count = select(func.count()).select_from(base.subquery()).subquery()
    page = base.order_by(Admission.created_at.desc(), Admission.id.desc()).limit(limit).offset(offset).subquery()
    episode = aliased(Admission, page)
    return session.execute(select(count.c[0], episode, Patient, Verification, AdmissionIntake, Site, Service)
        .select_from(count).outerjoin(page, true()).outerjoin(Patient, Patient.id == episode.patient_id)
        .outerjoin(Verification, Verification.patient_id == Patient.id)
        .outerjoin(AdmissionIntake, AdmissionIntake.admission_id == episode.id)
        .outerjoin(Site, Site.id == AdmissionIntake.site_id).outerjoin(Service, Service.id == AdmissionIntake.service_id)
        .order_by(episode.created_at.desc(), episode.id.desc())).all()


def project_page(rows, actor, limit, offset, longitudinal=False):
    items = []
    for _, episode, patient, verification, intake, site, service in rows:
        if episode is not None:
            item = {'episode': episode_projection(actor, episode, intake, site, service)}
            if not longitudinal:
                item['patient'] = patient_projection(actor, patient, verification)
            items.append(item)
    return {'items': items, 'total': rows[0][0], 'limit': limit, 'offset': offset}


def list_attentions(session, *, actor, request_id, limit=20, offset=0, type=None, site_id=None, service_id=None, patient_id=None):
    authorize(actor, 'clinical.attentions.read')
    with session.begin():
        validate_filters(session, site_id, service_id)
        criteria = [Admission.status == 'open']
        if patient_id is not None:
            if session.get(Patient, patient_id) is None:
                missing()
            criteria.append(Admission.patient_id == patient_id)
        if type is not None:
            criteria.append(Admission.type == type)
        if site_id is not None:
            criteria.append(AdmissionIntake.site_id == site_id)
        if service_id is not None:
            criteria.append(AdmissionIntake.service_id == service_id)
        result = project_page(attention_rows(session, criteria, limit, offset), actor, limit, offset)
        record_success(session, actor=actor, action='clinical.attentions.read', request_id=request_id, resource_id=patient_id)
    return result


def read_context(session, *, actor, request_id, episode_id=None, patient_id=None, limit=20, offset=0):
    authorize(actor, 'clinical.context.read')
    with session.begin():
        if episode_id is not None:
            rows = attention_rows(session, [Admission.id == episode_id], 1, 0)
            if not rows[0][0]:
                missing()
            result = project_page(rows, actor, 1, 0)['items'][0]
        else:
            patient = session.get(Patient, patient_id)
            if patient is None:
                missing()
            result = {'patient': patient_projection(actor, patient, session.get(Verification, patient_id))}
            if 'clinical.attentions.read' in actor.permissions:
                rows = attention_rows(session, [Admission.patient_id == patient_id], limit, offset)
                result['attentions'] = project_page(rows, actor, limit, offset, longitudinal=True)
        # V3-04–06 aún no existen: no fabricar resúmenes clínicos vacíos.
        record_success(session, actor=actor, action='clinical.context.read', request_id=request_id, resource_id=episode_id or patient_id)
    return result


def list_catalog(session, *, actor, request_id, kind, site_id=None, limit=20, offset=0):
    authorize(actor, 'clinical.catalogs.read')
    with session.begin():
        model = Site if kind == 'sites' else Service
        criteria = [model.active.is_(True)]
        if kind == 'services':
            validate_filters(session, site_id, None)
            criteria.append(Service.site_id == site_id)
        count = select(func.count()).select_from(model).where(*criteria).subquery()
        page = select(model).where(*criteria).order_by(model.code, model.id).limit(limit).offset(offset).subquery()
        item = aliased(model, page)
        rows = session.execute(select(count.c[0], item).select_from(count).outerjoin(page, true()).order_by(item.code, item.id)).all()
        fields = ('id', 'code', 'name') + (('site_id',) if kind == 'services' else ())
        result = {'items': [{k: getattr(row, k) for k in fields} for _, row in rows if row is not None],
                  'total': rows[0][0], 'limit': limit, 'offset': offset}
        record_success(session, actor=actor, action='clinical.catalogs.read', request_id=request_id)
    return result
