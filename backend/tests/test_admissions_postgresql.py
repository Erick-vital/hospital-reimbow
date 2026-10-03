from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime, timezone
from threading import Barrier
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import delete, event, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from hospital.admissions.models import Admission
from hospital.admissions.schemas import AdmissionCreate
from hospital.admissions.service import create_admission, list_admissions, read_admission
from hospital.audit.models import AuditEvent
from hospital.core.config import Settings
from hospital.core.database import Database
from hospital.core.errors import ApplicationError
from hospital.patients.models import Patient
from hospital.main import create_app
from test_patients_postgresql import actor_for, create as create_patient_http, headers

pytestmark = pytest.mark.integration


@pytest.fixture
def database():
    db = Database(Settings(app_env='test'))
    with db.engine.connect() as connection:
        assert connection.scalar(text('SELECT current_database()')) == 'hospital_test'
    yield db
    db.dispose()


@pytest.fixture
def sessions(database):
    with database.engine.connect() as connection:
        outer = connection.begin()
        factory = sessionmaker(bind=connection, join_transaction_mode='create_savepoint', expire_on_commit=False)
        yield factory
        outer.rollback()


@pytest.fixture
def client(sessions):
    with TestClient(create_app(Settings(app_env='test', dev_identity_enabled=True))) as client:
        client.app.state.database.sessions = sessions
        yield client


@pytest.fixture
def patient(client):
    response = create_patient_http(client, actor='admision-demo')
    assert response.status_code == 201
    return response.json()


def create(client, patient_id, type='emergency', actor='admision-demo'):
    return client.post('/api/v1/admissions', json={'patient_id': patient_id, 'type': type}, headers=headers(actor))


def test_unknown_patient_multiple_types_same_type_and_read(client, patient, sessions):
    assert patient['given_names'] is None and patient['birth_date'] is None and patient['identifiers'] == []
    before = datetime.now(timezone.utc)
    responses = [create(client, patient['id'], type=t) for t in ('emergency', 'outpatient', 'inpatient', 'emergency')]
    assert all(r.status_code == 201 for r in responses)
    episodes = [r.json() for r in responses]
    assert len({a['id'] for a in episodes}) == 4 and len({a['folio'] for a in episodes}) == 4
    for response, admission in zip(responses, episodes):
        assert admission['patient_id'] == patient['id'] and admission['status'] == 'open'
        assert admission['folio'].startswith('EPI-') and len(admission['folio']) >= 16
        assert admission['created_by'] == patient['created_by']
        assert before <= datetime.fromisoformat(admission['created_at']) <= datetime.now(timezone.utc)
        assert set(admission) == {'id', 'folio', 'patient_id', 'type', 'status', 'created_at', 'created_by'}
        read = client.get(response.headers['Location'], headers=headers('consulta-demo'))
        assert read.status_code == 200 and read.json() == admission
        with sessions() as session:
            row = session.scalar(select(AuditEvent).where(AuditEvent.request_id == UUID(response.headers['X-Request-ID'])))
            snapshot = row.event_metadata['new']
            assert datetime.fromisoformat(snapshot.pop('created_at')) == datetime.fromisoformat(admission['created_at'])
            assert snapshot == {k:v for k,v in admission.items() if k != 'created_at'}
            assert row.event_metadata['old'] is None and row.actor_id == UUID(patient['created_by'])
            assert row.resource_id == UUID(admission['id']) and row.action == 'admissions.create'
            read_event = session.scalar(select(AuditEvent).where(AuditEvent.request_id == UUID(read.headers['X-Request-ID'])))
            assert read_event.action == 'admissions.read' and read_event.event_metadata == {}


def test_paginated_list_isolated_order_and_empty(client, patient, sessions):
    other = create_patient_http(client).json()
    assert create(client, other['id']).status_code == 201
    # Empatar fechas para comprobar desempate estable por UUID.
    actor = UUID(patient['created_by'])
    ids = sorted([uuid4(), uuid4(), uuid4()])
    with sessions.begin() as session:
        session.add_all([Admission(id=id, patient_id=UUID(patient['id']), type='emergency', created_by=actor,
                                  created_at=datetime(2026,1,1,tzinfo=timezone.utc)) for id in reversed(ids)])
    path = f"/api/v1/patients/{patient['id']}/admissions"
    first = client.get(path+'?limit=2', headers=headers('consulta-demo'))
    assert first.status_code == 200
    assert first.json()['total'] == 3 and [a['id'] for a in first.json()['items']] == [str(i) for i in ids[:2]]
    second = client.get(path+'?limit=2&offset=2', headers=headers('consulta-demo'))
    assert [a['id'] for a in second.json()['items']] == [str(ids[2])]
    empty = client.get(path+'?offset=30', headers=headers())
    assert empty.json() == {'items': [], 'total':3, 'limit':20, 'offset':30}
    no_episodes = create_patient_http(client).json()
    assert client.get(f"/api/v1/patients/{no_episodes['id']}/admissions", headers=headers()).json()['total'] == 0
    with sessions() as session:
        row = session.scalar(select(AuditEvent).where(AuditEvent.request_id == UUID(first.headers['X-Request-ID'])))
        assert row.action == 'admissions.list' and row.event_metadata == {} and row.resource_id is None


@pytest.mark.parametrize('data', [{}, {'patient_id':'not-uuid','type':'emergency'}, {'patient_id':str(uuid4())}, {'patient_id':str(uuid4()),'type':'other'}, {'patient_id':None,'type':'emergency'}, {'patient_id':str(uuid4()),'type':None}])
def test_invalid_required_fields(client, data):
    response = client.post('/api/v1/admissions', json=data, headers=headers())
    assert response.status_code == 422 and response.json()['error']['code'] == 'VALIDATION_ERROR'


@pytest.mark.parametrize('field,value', [('id',str(uuid4())), ('folio','EPI-X'), ('status','open'), ('created_at','2026-01-01T00:00:00Z'), ('created_by',str(uuid4())), ('search_id',str(uuid4())), ('bed','FICTICIA')])
def test_server_fields_and_out_of_scope_rejected(client, patient, field, value):
    response = client.post('/api/v1/admissions', json={'patient_id':patient['id'], 'type':'emergency', field:value}, headers=headers())
    assert response.status_code == 422


@pytest.mark.parametrize('query', ['limit=0','limit=101','offset=-1','limit=x','offset=x'])
def test_list_validation(client, patient, query):
    assert client.get(f"/api/v1/patients/{patient['id']}/admissions?{query}", headers=headers()).status_code == 422


def test_not_found_no_success_audit_and_invalid_path(client, sessions):
    responses = [create(client, str(uuid4())), client.get('/api/v1/admissions/'+str(uuid4()), headers=headers()),
                 client.get('/api/v1/patients/'+str(uuid4())+'/admissions', headers=headers())]
    for response in responses:
        assert response.status_code == 404 and response.json()['error']['code'] == 'RESOURCE_NOT_FOUND'
        with sessions() as session:
            assert session.scalar(select(AuditEvent.id).where(AuditEvent.request_id == UUID(response.headers['X-Request-ID']))) is None
    for path in ('/api/v1/admissions/not-uuid', '/api/v1/patients/not-uuid/admissions'):
        assert client.get(path, headers=headers()).status_code == 422


@pytest.mark.parametrize('actor', [None,'inactivo-demo','desconocido'])
@pytest.mark.parametrize('operation', ['create','read','list'])
def test_401_before_lookup_denial_persists(client, database, actor, operation):
    h = headers(actor) if actor else {}
    patient_id = str(uuid4())
    if operation == 'create':
        response = client.post('/api/v1/admissions', json={'patient_id':patient_id, 'type':'emergency'}, headers=h)
    else:
        path = '/api/v1/admissions/'+patient_id if operation == 'read' else '/api/v1/patients/'+patient_id+'/admissions'
        response = client.get(path, headers=h)
    assert response.status_code == 401
    with database.sessions() as session:
        row = session.scalar(select(AuditEvent).where(AuditEvent.request_id == UUID(response.headers['X-Request-ID'])))
        assert row.action == 'admissions.'+operation and row.result == 'denied'
        assert row.actor_id is None and row.resource_id is None
        assert row.event_metadata == {'code':'IDENTITY_REQUIRED'}


def test_403_before_lookup_and_actor_cannot_choose_author(client, database):
    response = create(client, str(uuid4()), actor='consulta-demo')
    assert response.status_code == 403
    with database.sessions() as session:
        row = session.scalar(select(AuditEvent).where(AuditEvent.request_id == UUID(response.headers['X-Request-ID'])))
        assert row.action == 'admissions.create' and row.result == 'denied' and row.actor_id is not None
        assert row.resource_id is None and row.event_metadata == {'code':'PERMISSION_DENIED'}


@pytest.mark.parametrize('operation,permissions', [('create',{'admissions.read'}), ('read',{'admissions.create'}), ('list',{'admissions.read'}), ('list',{'patients.read'})])
def test_services_authorize_before_query(database, operation, permissions):
    actor = replace(actor_for(database), permissions=frozenset(permissions))
    with database.sessions() as session:
        with pytest.raises(ApplicationError) as error:
            if operation == 'create':
                create_admission(session, actor=actor, request_id=uuid4(), data=AdmissionCreate(patient_id=uuid4(),type='emergency'))
            elif operation == 'read':
                read_admission(session, actor=actor, request_id=uuid4(), admission_id=uuid4())
            else:
                list_admissions(session, actor=actor, request_id=uuid4(), patient_id=uuid4())
        assert error.value.status == 403 and not session.in_transaction()


def test_no_mutation_or_implicit_flows(client, patient):
    response = create(client, patient['id'])
    assert response.status_code == 201
    paths = client.get('/openapi.json').json()['paths']
    assert set(paths['/api/v1/admissions']) == {'post'}
    assert set(paths['/api/v1/admissions/{admission_id}']) == {'get'}
    assert set(paths['/api/v1/patients/{patient_id}/admissions']) == {'get'}
    for path in (response.headers['Location'], f"/api/v1/patients/{patient['id']}"):
        for method in ('put','patch','delete'):
            assert getattr(client, method)(path, headers=headers()).status_code == 405


@pytest.mark.parametrize('failure', ['audit_insert','after_audit_insert'])
def test_actual_admission_rollback_and_folio_gap(database, monkeypatch, failure):
    from hospital.admissions import service
    actor = actor_for(database)
    # Paciente confirmado visible desde conexiones independientes.
    with database.sessions.begin() as session:
        patient = Patient(identity_status='provisional', created_by=actor.id)
        session.add(patient)
        session.flush()
        patient_id = patient.id
    original = service.record_success
    correlation, allocated = uuid4(), []
    def fail(session, **kwargs):
        allocated.append((kwargs['resource_id'], session.get(Admission, kwargs['resource_id']).folio))
        original(session, **{**kwargs, 'request_id':None} if failure == 'audit_insert' else kwargs)
        if failure == 'after_audit_insert':
            raise RuntimeError('Fallo ficticio después de auditoría')
    monkeypatch.setattr(service, 'record_success', fail)
    with database.sessions() as session:
        with pytest.raises((IntegrityError, RuntimeError)):
            create_admission(session, actor=actor, request_id=correlation, data=AdmissionCreate(patient_id=patient_id,type='emergency'))
    monkeypatch.setattr(service, 'record_success', original)
    with database.sessions() as session:
        assert session.get(Admission, allocated[0][0]) is None
        assert session.scalar(select(AuditEvent.id).where(AuditEvent.request_id == correlation)) is None
    with database.sessions() as session:
        result = create_admission(session, actor=actor, request_id=uuid4(), data=AdmissionCreate(patient_id=patient_id,type='emergency'))
    assert int(result['folio'][4:]) > int(allocated[0][1][4:])


@pytest.mark.parametrize('operation', ['read','list'])
def test_reads_fail_closed_without_success_audit(client, patient, sessions, monkeypatch, operation):
    from hospital.admissions import service
    created = create(client, patient['id'])
    original = service.record_success
    def fail(session, **kwargs):
        original(session, **{**kwargs, 'request_id':None})
    monkeypatch.setattr(service, 'record_success', fail)
    path = created.headers['Location'] if operation == 'read' else f"/api/v1/patients/{patient['id']}/admissions"
    response = client.get(path, headers=headers())
    assert response.status_code == 503 and 'items' not in response.json()
    with sessions() as session:
        assert session.scalar(select(AuditEvent.id).where(AuditEvent.request_id == UUID(response.headers['X-Request-ID']))) is None


@pytest.mark.parametrize('changes', [{'type':'invalid'},{'status':'closed'},{'patient_id':uuid4()},{'created_by':uuid4()},{'folio':'bad'},{'type':None},{'patient_id':None}])
def test_database_checks_and_foreign_keys(client, patient, sessions, changes):
    with sessions() as session:
        with pytest.raises(IntegrityError):
            with session.begin():
                values = {'patient_id':UUID(patient['id']), 'created_by':UUID(patient['created_by']), 'type':'emergency', **changes}
                session.add(Admission(**values))
                session.flush()


def test_database_folio_unique_and_patient_delete_restricted(client, patient, sessions):
    created = create(client, patient['id']).json()
    with sessions() as session:
        with pytest.raises(IntegrityError):
            with session.begin():
                session.add(Admission(patient_id=UUID(patient['id']), created_by=UUID(patient['created_by']), type='emergency', folio=created['folio']))
                session.flush()
    with sessions() as session:
        with pytest.raises(IntegrityError):
            with session.begin():
                session.execute(delete(Patient).where(Patient.id == UUID(patient['id'])))
    with sessions() as session:
        assert session.get(Patient, UUID(patient['id'])) is not None
        assert session.get(Admission, UUID(created['id'])) is not None


def test_admission_folio_grows_without_touching_persistent_sequence(sessions):
    with sessions.begin() as session:
        session.execute(text('CREATE TEMP SEQUENCE admission_folio_seq START 1000000000000'))
        assert session.scalar(text('SELECT next_admission_folio()')) == 'EPI-1000000000000'


def test_concurrent_independent_episodes_same_patient_allowed(database):
    actor = actor_for(database)
    with database.sessions.begin() as session:
        patient = Patient(identity_status='provisional', created_by=actor.id)
        session.add(patient)
        session.flush()
        patient_id = patient.id
    barrier, pids = Barrier(2), []
    def wait_before_insert(conn, cursor, statement, parameters, context, executemany):
        if statement.startswith('INSERT INTO admissions '):
            pids.append(conn.connection.driver_connection.info.backend_pid)
            barrier.wait(timeout=10)
    event.listen(database.engine, 'before_cursor_execute', wait_before_insert)
    try:
        def worker(_):
            with database.sessions() as session:
                return create_admission(session, actor=actor, request_id=uuid4(), data=AdmissionCreate(patient_id=patient_id,type='emergency'))
        with ThreadPoolExecutor(max_workers=2) as executor:
            episodes = list(executor.map(worker, (0,1)))
    finally:
        event.remove(database.engine, 'before_cursor_execute', wait_before_insert)
    assert len(set(pids)) == 2
    assert len({a['id'] for a in episodes}) == 2 and len({a['folio'] for a in episodes}) == 2
    with database.sessions() as session:
        assert len(session.scalars(select(Admission).where(Admission.patient_id == patient_id)).all()) == 2
        for admission in episodes:
            assert len(session.scalars(select(AuditEvent).where(AuditEvent.resource_id == admission['id'], AuditEvent.action == 'admissions.create')).all()) == 1


def test_patient_disappearing_before_insert_returns_controlled_404(database):
    actor = actor_for(database)
    with database.sessions.begin() as session:
        patient = Patient(identity_status='provisional', created_by=actor.id)
        session.add(patient)
        session.flush()
        patient_id = patient.id
    # Recurso ficticio sin actividad. Simula una intervención externa a la API
    # después de la comprobación, para verificar traducción de la FK y rollback.
    def remove_before_insert(conn, cursor, statement, parameters, context, executemany):
        if statement.startswith('INSERT INTO admissions '):
            with database.sessions.begin() as other:
                other.execute(delete(Patient).where(Patient.id == patient_id))
    event.listen(database.engine, 'before_cursor_execute', remove_before_insert)
    correlation = uuid4()
    try:
        with database.sessions() as session:
            with pytest.raises(ApplicationError) as error:
                create_admission(session, actor=actor, request_id=correlation,
                                 data=AdmissionCreate(patient_id=patient_id, type='emergency'))
            assert error.value.status == 404 and not session.in_transaction()
    finally:
        event.remove(database.engine, 'before_cursor_execute', remove_before_insert)
    with database.sessions() as session:
        assert session.scalar(select(Admission.id).where(Admission.patient_id == patient_id)) is None
        assert session.scalar(select(AuditEvent.id).where(AuditEvent.request_id == correlation)) is None


def test_creation_permission_does_not_require_patient_read(database, sessions, patient):
    actor = replace(actor_for(database), permissions=frozenset({'admissions.create'}))
    with sessions() as session:
        episode = create_admission(session, actor=actor, request_id=uuid4(),
                                   data=AdmissionCreate(patient_id=UUID(patient['id']), type='emergency'))
    assert episode['patient_id'] == UUID(patient['id']) and 'given_names' not in episode
