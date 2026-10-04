"""C01–C04: lecturas reales PostgreSQL, permisos, proyección y auditoría."""
from dataclasses import replace
from uuid import UUID, uuid4

import pytest
from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import SQLAlchemyError

from hospital.administrative.models import Service, Site
from hospital.administrative.schemas import AdmissionCreateV2
from hospital.administrative.service import create_admission_v2
from hospital.audit.models import AuditEvent
from hospital.authorization.models import Permission, Role, RolePermission, UserRole
from hospital.clinical.service import list_attentions, read_context, list_catalog
from hospital.core.config import Settings
from hospital.core.errors import ApplicationError
from hospital.identity.models import User
from hospital.identity.seed import ROLE_PERMISSIONS, seed_local_identity
from test_administrative_v2 import make_patient, known
from test_patients_postgresql import actor_for, client, database, sessions, headers

pytestmark = pytest.mark.integration


@pytest.fixture
def clinical(sessions, database):
    with sessions() as session:
        seed_local_identity(session, Settings(app_env='test'))
    admin = actor_for(database)
    # Actores consultados desde la misma transacción de fixtures.
    from hospital.authorization.service import Actor
    with sessions() as session:
        user = session.scalar(select(User).where(User.actor_key == 'medico-demo'))
        medic = Actor(user.id, user.actor_key, ROLE_PERMISSIONS[user.actor_key])
    alfa = make_patient(sessions, admin, given_names='Alfa ficticia clínica', birth_date='1990-01-01', administrative_profile={'nationality': known('Dato restringido')})
    beta = make_patient(sessions, admin, given_names='Beta ficticia clínica')
    with sessions() as session:
        site = session.scalar(select(Site).where(Site.active.is_(True)))
        service = session.scalar(select(Service).where(Service.site_id == site.id, Service.active.is_(True)))
        site_id, service_id = site.id, service.id
    episodes = []
    for patient, kind, intake in [(alfa, 'outpatient', {'admitted_at': known('2026-01-01T10:00:00-06:00'), 'site_id': known(site_id), 'service_id': known(service_id), 'reason_for_visit': known('Motivo restringido')}), (alfa, 'emergency', {}), (beta, 'emergency', {})]:
        with sessions() as session:
            episodes.append(create_admission_v2(session, actor=admin, request_id=uuid4(), data=AdmissionCreateV2(patient_id=patient['id'], type=kind, intake=intake)))
    return medic, alfa, beta, episodes, site_id, service_id


def test_c01_seed_preserves_revocations_and_suspensions(sessions, clinical):
    with sessions.begin() as session:
        role = session.scalar(select(Role.id).where(Role.code == 'medico-demo'))
        permission = session.scalar(select(Permission.id).where(Permission.code == 'clinical.attentions.read'))
        session.execute(delete(RolePermission).where(RolePermission.role_id == role, RolePermission.permission_id == permission))
        session.execute(update(User).where(User.actor_key == 'enfermeria-demo').values(status='inactive'))
        nurse = session.scalar(select(User.id).where(User.actor_key == 'enfermeria-demo'))
        session.execute(delete(UserRole).where(UserRole.user_id == nurse))
        before = {u.actor_key: u.id for u in session.scalars(select(User))}
    for _ in range(2):
        with sessions() as session:
            seed_local_identity(session, Settings(app_env='test'))
    with sessions() as session:
        assert session.get(RolePermission, (role, permission)) is None
        assert not session.scalars(select(UserRole).where(UserRole.user_id == nurse)).all()
        assert session.scalar(select(User.status).where(User.actor_key == 'enfermeria-demo')) == 'inactive'
        assert before == {u.actor_key: u.id for u in session.scalars(select(User))}
    for key in ('admision-demo', 'supervisor-demo', 'consulta-demo'):
        assert not any(p.startswith('clinical.') for p in ROLE_PERMISSIONS[key])


def test_c02_page_filters_context_and_limited_projection(client, sessions, clinical):
    medic, alfa, beta, episodes, site_id, service_id = clinical
    hdr = headers('medico-demo')
    response = client.get('/api/v3/clinical/attentions', params={'site_id': str(site_id), 'service_id': str(service_id), 'type': 'outpatient', 'limit': 1}, headers=hdr)
    assert response.status_code == 200
    body = response.json()
    assert any(item['episode']['id'] == str(episodes[0]['id']) for item in body['items'])
    assert body['total'] >= 1 and body['limit'] == 1
    empty = client.get('/api/v3/clinical/attentions', params={'offset': 1000000}, headers=hdr).json()
    assert empty['items'] == [] and empty['total'] >= 3
    for episode in episodes:
        response = client.get(f"/api/v3/clinical/attentions/{episode['id']}/context", headers=hdr)
        assert response.status_code == 200
        assert response.headers['Cache-Control'] == 'no-store'
        item = response.json()
        assert set(item) == {'patient', 'episode'}
        assert set(item['patient']) == {'id','folio','given_names','family_name','second_family_name','identity_status','verification_quality'}
        assert set(item['episode']) == {'id','folio','patient_id','type','status','created_at','admitted_at','site','service'}
        assert item['episode']['patient_id'] == item['patient']['id']
        assert 'restringido' not in response.text
    item = client.get(f"/api/v3/clinical/attentions/{episodes[0]['id']}/context", headers=hdr).json()
    assert item['episode']['admitted_at']['value']== '2026-01-01T16:00:00Z'
    assert item['episode']['site']['value']['id'] == str(site_id)
    longitudinal = client.get(f"/api/v3/clinical/patients/{alfa['id']}/context", params={'limit': 1}, headers=hdr).json()
    assert longitudinal['attentions']['total'] == 2
    assert len(longitudinal['attentions']['items']) == 1
    other = client.get(f"/api/v3/clinical/patients/{beta['id']}/attentions", headers=hdr).json()
    assert other['total'] == 1 and other['items'][0]['episode']['id'] == str(episodes[2]['id'])
    with sessions() as session:
        event = session.scalar(select(AuditEvent).where(AuditEvent.request_id == UUID(response.headers['X-Request-ID'])))
        assert event.action == 'clinical.context.read' and event.event_metadata == {} and event.resource_type == 'clinical'


@pytest.mark.parametrize('params,status', [({'service_id': str(uuid4())},422), ({'type':'closed'},422), ({'limit':0},422), ({'offset':-1},422), ({'site_id':str(uuid4())},404)])
def test_c02_invalid_filters(client, clinical, params, status):
    assert client.get('/api/v3/clinical/attentions', params=params, headers=headers('medico-demo')).status_code == status


def test_c02_catalog_pair_and_historical_names(client, sessions, clinical):
    _, _, _, episodes, site_id, service_id = clinical
    with sessions.begin() as session:
        other = Site(code=uuid4().hex, name='Otra sede ficticia')
        session.add(other); session.flush(); other_id = other.id
    assert client.get('/api/v3/clinical/attentions', params={'site_id':str(other_id),'service_id':str(service_id)}, headers=headers('medico-demo')).status_code == 422
    with sessions.begin() as session:
        session.execute(update(Service).where(Service.id == service_id).values(active=False))
        session.execute(update(Site).where(Site.id == site_id).values(active=False))
    assert client.get('/api/v3/clinical/attentions', params={'site_id':str(site_id)}, headers=headers('medico-demo')).status_code == 404
    context = client.get(f"/api/v3/clinical/attentions/{episodes[0]['id']}/context", headers=headers('medico-demo')).json()
    assert context['episode']['site']['value']['id'] == str(site_id)
    sites = client.get('/api/v3/clinical/catalogs/sites', headers=headers('enfermeria-demo')).json()
    assert str(site_id) not in [s['id'] for s in sites['items']]


@pytest.mark.parametrize('actor,status', [('admision-demo',403),('supervisor-demo',403),('consulta-demo',403),('inactivo-demo',401),('medico-demo',200),('enfermeria-demo',200)])
def test_c04_all_routes_enforce_actor(client, clinical, actor, status):
    _, alfa, _, episodes, site_id, _ = clinical
    for path in ['/attentions',f"/attentions/{episodes[0]['id']}/context",f"/patients/{alfa['id']}/context",f"/patients/{alfa['id']}/attentions",'/catalogs/sites',f'/catalogs/services?site_id={site_id}']:
        response = client.get('/api/v3/clinical'+path, headers=headers(actor))
        assert response.status_code == status, path
        if status != 200:
            assert 'Alfa' not in response.text and 'PAC-' not in response.text


def test_c04_service_checks_and_section_omission(sessions, clinical):
    actor, alfa, _, episodes, _, _ = clinical
    restricted = replace(actor, permissions=actor.permissions - {'clinical.attentions.read'})
    with sessions() as session:
        result = read_context(session, actor=restricted, request_id=uuid4(), patient_id=alfa['id'])
        assert set(result) == {'patient'}
    for permission in ('patients.read','admissions.read','clinical.context.read'):
        denied = replace(actor, permissions=actor.permissions - {permission})
        for operation, args in [(read_context, {'episode_id':episodes[0]['id']}),(list_attentions, {})]:
            with sessions() as session, pytest.raises(ApplicationError) as exc:
                operation(session, actor=denied, request_id=uuid4(), **args)
            assert exc.value.status == 403
    with sessions() as session, pytest.raises(ApplicationError):
        list_catalog(session, actor=replace(actor, permissions=frozenset()), request_id=uuid4(), kind='sites')


def test_c04_http_revocation_and_not_found(client, sessions, clinical):
    _, alfa, _, episodes, _, _ = clinical
    with sessions.begin() as session:
        role = session.scalar(select(Role.id).where(Role.code == 'medico-demo'))
        permission = session.scalar(select(Permission.id).where(Permission.code == 'clinical.attentions.read'))
        session.execute(delete(RolePermission).where(RolePermission.role_id == role, RolePermission.permission_id == permission))
    assert client.get('/api/v3/clinical/attentions', headers=headers('medico-demo')).status_code == 403
    result = client.get(f"/api/v3/clinical/patients/{alfa['id']}/context", headers=headers('medico-demo')).json()
    assert set(result) == {'patient'}
    for path in [f'/attentions/{uuid4()}/context', f'/patients/{uuid4()}/context', f'/patients/{uuid4()}/attentions']:
        assert client.get('/api/v3/clinical'+path, headers=headers('enfermeria-demo')).status_code == 404


def test_c04_audit_failure_rolls_back_read(sessions, clinical, monkeypatch):
    from hospital.clinical import service
    actor, alfa, _, _, _, _ = clinical
    request_id = uuid4()
    original = service.record_success
    def fail(session, **kwargs):
        original(session, **kwargs)
        raise SQLAlchemyError('Fallo ficticio')
    monkeypatch.setattr(service, 'record_success', fail)
    with sessions() as session, pytest.raises(SQLAlchemyError):
        read_context(session, actor=actor, request_id=request_id, patient_id=alfa['id'])
    with sessions() as session:
        assert session.scalar(select(func.count()).select_from(AuditEvent).where(AuditEvent.request_id == request_id)) == 0


def test_c04_clinical_audit_visible_without_content(client, sessions, clinical):
    _, _, _, episodes, _, _ = clinical
    response = client.get(f"/api/v3/clinical/attentions/{episodes[0]['id']}/context", headers=headers('medico-demo'))
    assert response.status_code == 200
    audit = client.get('/api/v1/audit', params={'action':'clinical.context.read','resource_id':str(episodes[0]['id'])}, headers=headers())
    assert audit.status_code == 200
    assert audit.json()['total'] == 1
    event = audit.json()['items'][0]
    assert event['metadata'] == {} and event['resource_id'] == str(episodes[0]['id'])
    assert 'Alfa' not in audit.text and 'restringido' not in audit.text
    denied = client.get('/api/v3/clinical/attentions', headers=headers('consulta-demo'))
    with client.app.state.audit_sessions() as session:
        event = session.scalar(select(AuditEvent).where(AuditEvent.request_id == UUID(denied.headers['X-Request-ID'])))
        assert event.result == 'denied' and event.event_metadata == {'code':'PERMISSION_DENIED'}
        assert event.resource_id is None and event.resource_type == 'clinical'
