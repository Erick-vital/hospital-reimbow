from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from threading import Barrier
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import event, func, select, text, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from hospital.audit.models import AuditEvent
from hospital.authorization.service import Actor
from hospital.core.config import Settings
from hospital.core.database import Database
from hospital.core.errors import ApplicationError
from hospital.identity.models import User
from hospital.identity.seed import ROLE_PERMISSIONS
from hospital.main import create_app
from hospital.patients.models import Patient, PatientIdentifier, PatientSearch
from hospital.patients.schemas import PatientCreate, SearchFilters
from hospital.patients.service import create_patient, read_patient, search_patients

pytestmark = pytest.mark.integration


@pytest.fixture
def database():
    db = Database(Settings(app_env='test'))
    with db.engine.connect() as conn:
        assert conn.scalar(text('SELECT current_database()')) == 'hospital_test'
    yield db
    db.dispose()


@pytest.fixture
def sessions(database):
    with database.engine.connect() as conn:
        outer = conn.begin()
        factory = sessionmaker(bind=conn, join_transaction_mode='create_savepoint', expire_on_commit=False)
        yield factory
        outer.rollback()


@pytest.fixture
def client(sessions):
    with TestClient(create_app(Settings(app_env='test', dev_identity_enabled=True))) as c:
        c.app.state.database.sessions = sessions
        yield c


def headers(actor='supervisor-demo'):
    return {'X-Dev-Actor': actor}


def search(client, actor='supervisor-demo', **filters):
    response = client.get('/api/v1/patients', params=filters or {'unidentified': True}, headers=headers(actor))
    assert response.status_code == 200, response.text
    return response.json()


def create(client, actor='supervisor-demo', **data):
    identifiers = data.get('identifiers', [])
    if identifiers:
        filters = dict(identifier_system=identifiers[0]['system'], identifier_value=identifiers[0]['value'])
    elif any(data.get(k) for k in ('given_names', 'family_name', 'second_family_name')):
        filters = dict(name=' '.join(data[k].strip() for k in ('given_names', 'family_name', 'second_family_name') if data.get(k)))
    else:
        filters = dict(unidentified=True)
    evidence = search(client, actor, **filters)
    return client.post('/api/v1/patients', json={'identity_status': 'provisional', **data, 'search_id': evidence['search_id']}, headers=headers(actor))


def test_two_unknown_patients_read_location_and_audit(client, sessions):
    responses = [create(client, actor='admision-demo') for _ in range(2)]
    assert [r.status_code for r in responses] == [201, 201]
    first, second = [r.json() for r in responses]
    assert first['id'] != second['id'] and first['folio'] != second['folio']
    assert first['folio'].startswith('PAC-') and len(first['folio']) >= 16
    assert first['birth_date'] is None and first['given_names'] is None and first['identifiers'] == []
    read = client.get(responses[0].headers['Location'], headers=headers('admision-demo'))
    assert read.status_code == 200 and read.json() == first
    with sessions() as session:
        row = session.scalar(select(AuditEvent).where(AuditEvent.request_id == UUID(responses[0].headers['X-Request-ID'])))
        snapshot = row.event_metadata['new']
        assert datetime.fromisoformat(snapshot['created_at']) == datetime.fromisoformat(first['created_at'])
        assert {k:v for k,v in snapshot.items() if k != 'created_at'} == {k:v for k,v in first.items() if k != 'created_at'}
        assert row.event_metadata['old'] is None
        assert row.actor_id == UUID(first['created_by'])
        assert session.scalar(select(AuditEvent).where(AuditEvent.request_id == UUID(read.headers['X-Request-ID']))).event_metadata == {}


def test_normalization_search_projection_literal_and_candidates(client):
    value = 'DEMO-' + uuid4().hex
    data = dict(given_names='  Jose\u0301_%  ', family_name=' Ficticio ', birth_date='1990-01-01', identifiers=[{'system': 'test', 'value': value.lower()}])
    first = create(client, **data)
    assert first.status_code == 201
    patient = first.json()
    assert patient['given_names'] == 'José_%'
    assert patient['identifiers'] == [{'system': 'TEST', 'value': value.upper()}]
    assert create(client, given_names='José_%', family_name='Ficticio').status_code == 201
    assert create(client, given_names='JoséAB', family_name='Ficticio').status_code == 201
    for filters in (dict(folio=patient['folio']), dict(identifier_system='test', identifier_value=value.lower())):
        page = search(client, **filters)
        assert page['total'] == 1 and page['items'][0] == patient
    page = search(client, 'consulta-demo', name='JOSÉ_%', limit=1)
    assert page['total'] == 2 and len(page['items']) == 1
    assert set(page['items'][0]) == {'id', 'folio', 'identity_status', 'given_names', 'family_name', 'second_family_name'}
    second = search(client, 'consulta-demo', name='JOSÉ_%', limit=1, offset=1)
    assert second['items'][0]['id'] != page['items'][0]['id']
    assert search(client, name='José_%', offset=50)['total'] == 2
    assert search(client, name='José_%', offset=50)['items'] == []
    assert search(client, name='Jose_%')['total'] == 0
    assert search(client, name='José_%', folio=patient['folio'])['total'] == 1
    assert search(client, name='Otro', folio=patient['folio'])['total'] == 0
    limited = client.get(first.headers['Location'], headers=headers('consulta-demo'))
    assert limited.status_code == 200 and set(limited.json()) == set(page['items'][0])


@pytest.mark.parametrize('filters', [{}, {'name':' '}, {'name':''}, {'name':'x'*303}, {'identifier_system':'TEST'}, {'identifier_value':'DEMO'}, {'unidentified':True,'name':'Demo'}, {'unidentified':False}, {'name':'Demo','limit':0}, {'name':'Demo','limit':101}, {'name':'Demo','offset':-1}, {'identifier_system':'CURP','identifier_value':'SHORT'}, {'identifier_system':'TEST','identifier_value':'ß'}, {'name':'Demo','extra':'x'}])
def test_invalid_search(client, filters):
    response = client.get('/api/v1/patients', params=filters, headers=headers())
    assert response.status_code == 422
    assert response.json()['error']['code'] == 'VALIDATION_ERROR'


@pytest.mark.parametrize('data', [dict(given_names=' '), dict(identity_status='verified'), dict(birth_date='2999-01-01'), dict(identifiers=[{'system':'CURP','value':'SHORT'}]), dict(identifiers=[{'system':'TEST','value':'x y'}]), dict(identifiers=[{'system':'TEST','value':'a'},{'system':'test','value':' A '}]), dict(identifiers=[{'system':'TEST','value':str(i)} for i in range(11)]), dict(created_by=str(uuid4())), dict(id=str(uuid4())), dict(folio='PAC-X'), dict(identity_status='invalid')])
def test_invalid_create(client, data):
    response = client.post('/api/v1/patients', json={'identity_status':'provisional', **data}, headers=headers())
    assert response.status_code == 422 and response.json()['error']['code'] == 'VALIDATION_ERROR'
    assert '2999-01-01' not in response.text


@pytest.mark.parametrize('case', ['missing','random','foreign','expired','name','identifier','unidentified','folio','extra_name'])
def test_search_binding_and_expiry(client, sessions, case):
    data = {'identity_status':'provisional'}
    if case == 'missing':
        pass
    elif case == 'random':
        data['search_id'] = str(uuid4())
    else:
        filters = {'unidentified': True}
        actor = 'admision-demo' if case == 'foreign' else 'supervisor-demo'
        if case == 'name':
            filters = {'name':'Nombre distinto'}; data['given_names'] = 'Nombre solicitado'
        elif case == 'identifier':
            filters = {'identifier_system':'TEST','identifier_value':'OTRO'}; data['identifiers'] = [{'system':'TEST','value':'DEMO'}]
        elif case == 'unidentified':
            data['given_names'] = 'Persona conocida'
        elif case == 'folio':
            filters = {'folio':'PAC-000000000001'}
        elif case == 'extra_name':
            filters = {'identifier_system':'TEST','identifier_value':'DEMO','name':'Distinto'}
            data.update(given_names='Persona', identifiers=[{'system':'TEST','value':'DEMO'}])
        data['search_id'] = search(client, actor, **filters)['search_id']
        if case == 'expired':
            with sessions.begin() as session:
                session.execute(update(PatientSearch).where(PatientSearch.id == UUID(data['search_id'])).values(
                    created_at=datetime.now(timezone.utc)-timedelta(hours=1), expires_at=datetime.now(timezone.utc)-timedelta(minutes=1)))
    response = client.post('/api/v1/patients', json=data, headers=headers())
    assert response.status_code == 422 and response.json()['error']['code'] == 'SEARCH_REQUIRED'


def test_verified_permission_and_all_identifier_conflicts(client):
    value = uuid4().hex
    identifiers = [{'system':'TEST','value':value}]
    denied = create(client, actor='admision-demo', identity_status='verified', given_names='Persona ficticia', identifiers=identifiers)
    assert denied.status_code == 403
    first = create(client, identity_status='verified', given_names='Persona ficticia', identifiers=identifiers)
    assert first.status_code == 201 and first.json()['identity_status'] == 'verified'
    # Buscar identificador libre, pero duplicar el segundo también debe fallar.
    second = create(client, identifiers=[{'system':'TEST','value':uuid4().hex}, *identifiers])
    assert second.status_code == 409
    assert first.json()['id'] not in second.text
    assert second.json()['error']['code'] == 'IDENTIFIER_CONFLICT'
    assert create(client, identity_status='verified', given_names='Sin CURP').status_code == 201


@pytest.mark.parametrize('actor,status', [(None,401),('inactivo-demo',401),('no-existe',401),('consulta-demo',403)])
def test_authorization_before_resource_and_independent_denial(client, database, actor, status):
    response = client.post('/api/v1/patients', json={'identity_status':'provisional'}, headers=headers(actor) if actor else {})
    assert response.status_code == status
    with database.sessions() as session:
        row = session.scalar(select(AuditEvent).where(AuditEvent.request_id == UUID(response.headers['X-Request-ID'])))
        assert row.result == 'denied' and row.action == 'patients.create' and row.resource_id is None
        assert set(row.event_metadata) == {'code'}


def test_not_found_validation_and_no_mutation(client):
    assert client.get('/api/v1/patients/'+str(uuid4()), headers=headers()).status_code == 404
    assert client.get('/api/v1/patients/not-uuid', headers=headers()).status_code == 422
    assert client.get('/api/v1/patients/'+str(uuid4())).status_code == 401
    paths = client.get('/openapi.json').json()['paths']
    assert set(paths['/api/v1/patients']) == {'get','post'}
    assert set(paths['/api/v1/patients/{patient_id}']) == {'get'}
    for method in ('put','patch','delete'):
        assert getattr(client, method)('/api/v1/patients/'+str(uuid4()), headers=headers()).status_code == 405


def actor_for(database, key='supervisor-demo'):
    with database.sessions() as session:
        user = session.scalar(select(User).where(User.actor_key == key))
        return Actor(user.id, key, ROLE_PERMISSIONS[key])


@pytest.mark.parametrize('failure', ['audit_insert','after_audit_insert'])
def test_real_patient_audit_rollback_and_sequence_gap(database, monkeypatch, failure):
    from hospital.patients import service
    actor = actor_for(database)
    with database.sessions() as session:
        evidence = search_patients(session, actor=actor, request_id=uuid4(), filters=SearchFilters(unidentified=True))
    original = service.record_success
    correlation = uuid4()
    allocated = []
    def fail(session, **kwargs):
        allocated.append((kwargs['resource_id'], session.get(Patient, kwargs['resource_id']).folio))
        if failure == 'audit_insert':
            original(session, **{**kwargs, 'request_id': None})
        else:
            original(session, **kwargs)
            raise RuntimeError('Fallo ficticio después del evento')
    monkeypatch.setattr(service, 'record_success', fail)
    with database.sessions() as session:
        with pytest.raises((IntegrityError, RuntimeError)):
            create_patient(session, actor=actor, request_id=correlation, data=PatientCreate(identity_status='provisional', search_id=evidence['search_id']))
    monkeypatch.setattr(service, 'record_success', original)
    with database.sessions() as session:
        assert session.get(Patient, allocated[0][0]) is None
        assert session.scalar(select(AuditEvent.id).where(AuditEvent.request_id == correlation)) is None
        result = create_patient_after_no_transaction(database, actor, evidence)
        assert int(result['folio'][4:]) > int(allocated[0][1][4:])


def create_patient_after_no_transaction(database, actor, evidence):
    with database.sessions() as session:
        return create_patient(session, actor=actor, request_id=uuid4(), data=PatientCreate(identity_status='provisional', search_id=evidence['search_id']))


def test_reads_and_search_rollback_if_audit_fails(client, sessions, monkeypatch):
    from hospital.patients import service
    patient = create(client).json()
    original = service.record_success
    def fail(session, **kwargs):
        return original(session, **{**kwargs, 'request_id': None})
    monkeypatch.setattr(service, 'record_success', fail)
    for path in ('/api/v1/patients?unidentified=true','/api/v1/patients/'+patient['id']):
        response = client.get(path, headers=headers())
        assert response.status_code == 503 and 'items' not in response.json()
        with sessions() as session:
            assert session.scalar(select(AuditEvent.id).where(AuditEvent.request_id == UUID(response.headers['X-Request-ID']))) is None


@pytest.mark.parametrize('identity_status', ['provisional','verified'])
def test_true_concurrent_normalized_identifier_http(database, identity_status):
    key = 'RACE-' + uuid4().hex.upper()
    # APIs independientes, conexiones reales y barrera después de la lectura de
    # duplicados y antes del INSERT. Ambas transacciones ven el identificador libre.
    apps = [create_app(Settings(app_env='test', dev_identity_enabled=True)) for _ in range(2)]
    with TestClient(apps[0]) as c1, TestClient(apps[1]) as c2:
        searches = [search(c, identifier_system='TEST', identifier_value=key) for c in (c1,c2)]
        barrier = Barrier(2)
        pids = []
        def pause(conn, cursor, statement, params, context, executemany):
            if statement.startswith('INSERT INTO patients '):
                pids.append(conn.connection.driver_connection.info.backend_pid)
                barrier.wait(timeout=10)
        for app in apps:
            event.listen(app.state.database.engine, 'before_cursor_execute', pause)
        try:
            def worker(index):
                client = (c1,c2)[index]
                return client.post('/api/v1/patients', json={
                    'search_id':searches[index]['search_id'], 'identity_status':identity_status,
                    'given_names':'Persona concurrente ficticia',
                    'identifiers':[{'system':'test', 'value': key.lower() if index else ' '+key+' '}],
                }, headers=headers())
            with ThreadPoolExecutor(max_workers=2) as executor:
                responses = list(executor.map(worker, (0,1)))
        finally:
            for app in apps:
                event.remove(app.state.database.engine, 'before_cursor_execute', pause)
    assert sorted(r.status_code for r in responses) == [201,409]
    assert len(set(pids)) == 2
    with database.sessions() as session:
        patients = session.scalars(select(Patient).join(PatientIdentifier).where(PatientIdentifier.value == key)).all()
        assert len(patients) == 1
        events = session.scalars(select(AuditEvent).where(AuditEvent.resource_id == patients[0].id, AuditEvent.action == 'patients.create')).all()
        assert len(events) == 1
        loser = next(r for r in responses if r.status_code == 409)
        assert session.scalar(select(AuditEvent.id).where(AuditEvent.request_id == UUID(loser.headers['X-Request-ID']))) is None


@pytest.mark.parametrize('changes', [{'identity_status':'other'},{'identity_status':'verified'},{'given_names':''},{'birth_date':datetime(2999,1,1).date()},{'created_by':uuid4()},{'folio':'bad'}])
def test_database_patient_constraints(sessions, database, changes):
    actor = actor_for(database)
    with sessions() as session:
        with pytest.raises(IntegrityError):
            with session.begin():
                session.add(Patient(**{'identity_status':'provisional','created_by':actor.id, **changes}))
                session.flush()


@pytest.mark.parametrize('system,value', [('CURP','SHORT'),('TEST','lowercase'),('OTHER','ABC'),('TEST',''),('TEST','A B')])
def test_database_identifier_constraints(sessions, database, system, value):
    actor = actor_for(database)
    with sessions() as session:
        with pytest.raises(IntegrityError):
            with session.begin():
                patient = Patient(identity_status='provisional', created_by=actor.id)
                session.add(patient); session.flush()
                session.add(PatientIdentifier(patient_id=patient.id, system=system, value=value)); session.flush()


def test_valid_name_extremes_and_curp_structure(client):
    assert create(client, given_names='X').status_code == 201
    long_name = 'A' * 100
    assert create(client, given_names=long_name, family_name=long_name, second_family_name=long_name).status_code == 201
    # Dato sintético de estructura válida; no se certifica CURP real.
    curp = 'TEST' + uuid4().hex[:14].upper()
    response = create(client, identifiers=[{'system':'CURP','value':curp}])
    assert response.status_code == 201
    assert search(client, identifier_system='curp', identifier_value=curp.lower())['total'] == 1


def test_service_authorization_before_patient_lookup(database):
    actor = actor_for(database)
    from dataclasses import replace
    from hospital.patients.service import read_patient
    with database.sessions() as session:
        with pytest.raises(ApplicationError) as error:
            read_patient(session, actor=replace(actor, permissions=frozenset({'patients.read_demographics'})), request_id=uuid4(), patient_id=uuid4())
        assert error.value.status == 403 and not session.in_transaction()


def test_expired_search_search_rollback_and_identifier_fk(sessions, database, client, monkeypatch):
    actor = actor_for(database)
    from hospital.patients import service
    original = service.record_success
    with sessions() as session:
        before = session.scalar(select(func.count()).select_from(PatientSearch))
    def fail(session, **kwargs):
        original(session, **kwargs)
        raise RuntimeError('Fallo ficticio después de búsqueda')
    monkeypatch.setattr(service, 'record_success', fail)
    assert client.get('/api/v1/patients?unidentified=true', headers=headers()).status_code == 500
    with sessions() as session:
        assert session.scalar(select(func.count()).select_from(PatientSearch)) == before
    with sessions() as session:
        with pytest.raises(IntegrityError):
            with session.begin():
                session.add(PatientIdentifier(patient_id=uuid4(), system='TEST', value=uuid4().hex.upper()))
                session.flush()


def test_folio_grows_past_minimum_without_resetting_real_sequence(sessions):
    # Secuencia temporal que oculta la real sólo durante esta transacción;
    # no reinicia ni consume la secuencia persistente.
    with sessions.begin() as session:
        session.execute(text('CREATE TEMP SEQUENCE patient_folio_seq START 1000000000000'))
        assert session.scalar(text('SELECT next_patient_folio()')) == 'PAC-1000000000000'
