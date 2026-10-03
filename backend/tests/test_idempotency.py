"""I01–I13/A09: API, restricciones SQL y conexiones PostgreSQL independientes."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import timedelta
from threading import Barrier
from time import monotonic
from uuid import UUID, uuid1, uuid4

import pytest
from sqlalchemy import delete, func, select, text, update
from sqlalchemy.exc import IntegrityError

from hospital.administrative.models import Verification, VerificationEvidence
from hospital.administrative.schemas import AdmissionCreateV2, PatientCreateV2
from hospital.administrative.service import create_admission_v2, create_patient_v2
from hospital.audit.models import AuditEvent
from hospital.authorization.models import Permission, Role, RolePermission
from hospital.core.errors import ApplicationError
from hospital.idempotency.models import IdempotencyRecord
from hospital.idempotency.service import reserve
from hospital.identity.models import User
from hospital.patients.models import Patient, PatientSearch
from hospital.patients.schemas import SearchFilters
from hospital.patients.service import search_patients
from test_administrative_v2 import verified_data, known, make_patient
from test_patients_postgresql import actor_for, client, database, sessions, headers

pytestmark = pytest.mark.integration


def payload(client, version='v2', actor='supervisor-demo', **fields):
    body = {'identity_status': 'provisional', **fields}
    if body.get('identifiers'):
        first = body['identifiers'][0]
        filters = {'identifier_system': first['system'], 'identifier_value': first['value']}
    elif body.get('given_names'):
        filters = {'name': ' '.join(body.get(f, '').strip() for f in ('given_names','family_name','second_family_name') if body.get(f))}
    else:
        filters = {'unidentified': True}
    search = client.get('/api/' + version + '/patients', headers=headers(actor), params=filters)
    assert search.status_code == 200
    return {**body, 'search_id': search.json()['search_id']}


def post(client, body, key, kind='patients', version='v2', actor='supervisor-demo'):
    return client.post('/api/' + version + '/' + kind, json=body,
                       headers={**headers(actor), 'Idempotency-Key': str(key)})


@pytest.mark.parametrize('version', ['v1','v2'])
def test_i01_i09_i13_replay_expired_search_headers_audit(client, sessions, version):
    key = uuid4()
    body = payload(client, version)
    first = post(client, body, key, version=version)
    assert first.status_code == 201
    with sessions.begin() as s:
        s.execute(update(PatientSearch).where(PatientSearch.id == UUID(body['search_id'])).values(created_at=func.clock_timestamp()-text("interval '16 minutes'"), expires_at=func.clock_timestamp()-text("interval '1 minute'")))
    again = post(client, body, str(key).upper(), version=version)
    assert again.status_code == 200 and first.json() == again.json()
    for field in ('Location','Idempotency-Expires-At'):
        assert first.headers[field] == again.headers[field]
    assert first.headers['Idempotency-Replayed'] == 'false' and again.headers['Idempotency-Replayed'] == 'true'
    assert first.headers['X-Request-ID'] != again.headers['X-Request-ID']
    assert again.headers['Cache-Control'] == 'no-store'
    with sessions() as s:
        events = s.scalars(select(AuditEvent).where(AuditEvent.resource_id == UUID(first.json()['id'])).order_by(AuditEvent.created_at, AuditEvent.id)).all()
        assert [e.action for e in events] == ['patients.create','patients.replay']
        assert events[-1].event_metadata == {}
    rejected = post(client, body, uuid4(), version=version)
    assert rejected.status_code == 422 and rejected.json()['error']['code'] == 'SEARCH_REQUIRED'
    renewed = payload(client, version)
    assert post(client, renewed, key, version=version).status_code == 200
    # V1 no consume acuse; dos claves nuevas con el mismo acuse crean dos altas.
    assert post(client, renewed, uuid4(), version=version).status_code == 201
    assert post(client, renewed, uuid4(), version=version).status_code == 201


@pytest.mark.parametrize('version', ['v1','v2'])
def test_i02_normalized_fingerprint_and_conflict(client, version):
    value = uuid4().hex.upper()
    body = payload(client, version, given_names='  Jose\u0301 ', identifiers=[{'system':'test','value':value}, {'system':'TEST','value':value+'-2'}])
    key = uuid4()
    assert post(client, body, key, version=version).status_code == 201
    equivalent = {**body, 'given_names':'José', 'birth_date':None,
                  'identifiers': list(reversed(body['identifiers']))}
    assert post(client, equivalent, key, version=version).status_code == 200
    changed = {**equivalent, 'birth_date':'1990-01-01'}
    conflict = post(client, changed, key, version=version)
    assert conflict.status_code == 409 and conflict.json()['error']['code'] == 'IDEMPOTENCY_CONFLICT'
    assert str(key) not in conflict.text and 'fingerprint' not in conflict.text


@pytest.mark.parametrize('kind', ['patients','admissions'])
@pytest.mark.parametrize('bad', ['', 'bad', str(uuid1()), '{'+str(uuid4())+'}', str(uuid4()).replace('-','')])
def test_i03_invalid_key(client, kind, bad):
    body = {'identity_status':'provisional'} if kind == 'patients' else {'patient_id':str(uuid4()),'type':'emergency'}
    assert post(client, body, bad, kind=kind).status_code == 422


def test_i03_missing_duplicate_v1_compatible(client):
    body = payload(client)
    assert client.post('/api/v2/patients', json=body, headers=headers()).status_code == 422
    assert client.post('/api/v2/admissions', json={'patient_id':str(uuid4()),'type':'emergency'}, headers=headers()).status_code == 422
    repeated = [('X-Dev-Actor','supervisor-demo'), ('Idempotency-Key',str(uuid4())), ('Idempotency-Key',str(uuid4()))]
    assert client.post('/api/v2/patients', json=body, headers=repeated).status_code == 422
    assert client.post('/api/v1/patients', json=body, headers=headers()).status_code == 201


def test_i04_a09_actor_operation_version_isolation(client):
    key = uuid4()
    one = post(client, payload(client), key)
    two = post(client, payload(client, 'v1'), key, version='v1')
    three = post(client, payload(client, actor='admision-demo'), key, actor='admision-demo')
    assert all(r.status_code == 201 for r in (one,two,three))
    assert len({r.json()['id'] for r in (one,two,three)}) == 3
    body = {'patient_id':one.json()['id'], 'type':'emergency'}
    v2 = post(client, body, key, kind='admissions')
    v1 = post(client, body, key, kind='admissions', version='v1')
    assert v2.status_code == v1.status_code == 201 and v2.json()['id'] != v1.json()['id']
    assert post(client, body, key, kind='admissions', version='v1').json() == v1.json()
    assert post(client, body, key, kind='admissions').json() == v2.json()


@pytest.mark.parametrize('field', ['profile','absence','description','verification','intake'])
def test_a09_complete_business_fingerprint(client, field):
    body = payload(client, **verified_data()) if field=='verification' else payload(client, **({'is_unidentified':True} if field == 'description' else {}))
    key = uuid4()
    kind = 'patients'
    if field == 'intake':
        patient = post(client, body, uuid4()).json()
        body = {'patient_id':patient['id'],'type':'emergency'}
        kind = 'admissions'
    first = post(client, body, key, kind=kind)
    assert first.status_code == 201
    changed = deepcopy(body)
    if field == 'profile': changed['administrative_profile'] = {'nationality':known('País ficticio')}
    elif field == 'absence': changed['administrative_profile'] = {'nationality':{'state':'unknown'}}
    elif field == 'description': changed['unidentified_description'] = {'identifying_features':known('Descripción ficticia')}
    elif field == 'verification': changed['verification'][0]['source_reference'] = 'Otro documento ficticio'
    else: changed['intake'] = {'origin':known('Procedencia ficticia')}
    error = post(client, changed, key, kind=kind)
    assert error.status_code == 409 and error.json()['error']['code'] == 'IDEMPOTENCY_CONFLICT'
    assert post(client, body, key, kind=kind).json() == first.json()


def test_i05_i13_creation_replay_audit_failure_rolls_back(client, sessions, monkeypatch):
    from hospital.administrative import service
    from hospital.idempotency import service as idempotency
    original = service.record_success
    body, key = payload(client), uuid4()
    def fail(s, **kw):
        original(s, **{**kw, 'request_id':None})
    monkeypatch.setattr(service, 'record_success', fail)
    assert post(client, body, key).status_code == 503
    with sessions() as s:
        assert s.scalar(select(IdempotencyRecord).where(IdempotencyRecord.key==key)) is None
    monkeypatch.setattr(service, 'record_success', original)
    first = post(client, body, key)
    assert first.status_code == 201
    monkeypatch.setattr(idempotency, 'record_success', fail)
    assert post(client, body, key).status_code == 503
    with sessions() as s:
        assert s.scalar(select(func.count()).select_from(AuditEvent).where(AuditEvent.resource_id==UUID(first.json()['id']))) == 1
    monkeypatch.setattr(idempotency, 'record_success', original)
    assert post(client, body, key).status_code == 200


def test_i05_direct_sql_pending_cannot_commit(database):
    actor = actor_for(database)
    key = uuid4()
    with database.sessions() as s, pytest.raises(IntegrityError):
        with s.begin():
            s.execute(text("INSERT INTO idempotency_records (actor_id,operation,key,fingerprint) VALUES (:actor,'v2.patients.create',:key,:digest)"),
                      {'actor':actor.id,'key':key,'digest':'0'*64})
    with database.sessions() as s:
        assert s.scalar(select(IdempotencyRecord).where(IdempotencyRecord.key==key)) is None


@pytest.mark.parametrize('permission', ['patients.create','patients.verify_identity','patients.read_demographics'])
def test_i10_current_permissions_and_a09_evidence(client, sessions, permission):
    body, key = payload(client, **verified_data()), uuid4()
    first = post(client, body, key)
    assert first.status_code == 201
    with sessions.begin() as s:
        role = s.scalar(select(Role.id).where(Role.code=='supervisor-demo'))
        perm = s.scalar(select(Permission.id).where(Permission.code==permission))
        s.execute(delete(RolePermission).where(RolePermission.role_id==role, RolePermission.permission_id==perm))
    repeated = post(client, body, key)
    if permission == 'patients.read_demographics':
        assert repeated.status_code == 200 and 'verification' not in repeated.json() and 'birth_date' not in repeated.json()
    else:
        assert repeated.status_code == 403
    with sessions() as s:
        assert s.scalar(select(func.count()).select_from(Verification).where(Verification.patient_id==UUID(first.json()['id']))) == 1
        assert s.scalar(select(func.count()).select_from(VerificationEvidence).where(VerificationEvidence.patient_id==UUID(first.json()['id']))) == 2


def test_i10_inactive_mode_and_admission_permissions(client, sessions):
    body, key = payload(client), uuid4()
    first = post(client, body, key)
    admission = {'patient_id':first.json()['id'], 'type':'emergency'}
    episode_key = uuid4()
    assert post(client, admission, episode_key, kind='admissions').status_code == 201
    with sessions.begin() as s:
        role = s.scalar(select(Role.id).where(Role.code=='supervisor-demo'))
        for code in ('admissions.read','admissions.read_intake','patients.read'):
            perm = s.scalar(select(Permission.id).where(Permission.code==code))
            s.execute(delete(RolePermission).where(RolePermission.role_id==role, RolePermission.permission_id==perm))
    assert post(client, body, key).status_code == 200  # Crear no exige leer.
    projected = post(client, admission, episode_key, kind='admissions')
    assert projected.status_code == 200 and 'intake' not in projected.json()
    with sessions.begin() as s:
        perm = s.scalar(select(Permission.id).where(Permission.code=='admissions.create'))
        s.execute(delete(RolePermission).where(RolePermission.role_id==role, RolePermission.permission_id==perm))
    assert post(client, admission, episode_key, kind='admissions').status_code == 403
    with sessions.begin() as s:
        s.execute(update(User).where(User.actor_key=='supervisor-demo').values(status='inactive'))
    assert post(client, body, key).status_code == 401
    client.app.state.settings.dev_identity_enabled = False
    assert post(client, body, key).status_code == 401


def test_i11_database_clock_window_and_reserved_expiration(client, sessions):
    body, key = payload(client), uuid4()
    first = post(client, body, key)
    assert first.status_code == 201
    with sessions.begin() as s:
        now = s.scalar(select(func.clock_timestamp()))
        s.execute(update(IdempotencyRecord).where(IdempotencyRecord.key==key).values(created_at=now-timedelta(hours=24)+timedelta(seconds=2), expires_at=now+timedelta(seconds=2)))
    assert post(client, body, key).status_code == 200
    with sessions.begin() as s:
        now = s.scalar(select(func.clock_timestamp()))
        s.execute(update(IdempotencyRecord).where(IdempotencyRecord.key==key).values(created_at=now-timedelta(hours=24,seconds=1),expires_at=now-timedelta(seconds=1)))
    error = post(client, body, key)
    assert error.status_code == 409 and error.json()['error']['code']=='IDEMPOTENCY_EXPIRED'
    with sessions() as s:
        assert s.scalar(select(IdempotencyRecord).where(IdempotencyRecord.key==key)).patient_id == UUID(first.json()['id'])
        assert s.scalar(select(func.count()).select_from(AuditEvent).where(AuditEvent.action=='patients.create',AuditEvent.resource_id==UUID(first.json()['id']))) == 1


@pytest.mark.parametrize('kind', ['patients','admissions'])
@pytest.mark.parametrize('same_key', [True, False])
def test_i06_i08_real_connections_barrier(database, kind, same_key):
    actor = actor_for(database)
    barrier = Barrier(2)
    key = uuid4()
    pids = []
    if kind == 'patients':
        with database.sessions() as s:
            search = search_patients(s, actor=actor, request_id=uuid4(), filters=SearchFilters(unidentified=True))
        data = PatientCreateV2(identity_status='provisional',search_id=search['search_id'])
        creator = create_patient_v2
    else:
        patient = make_patient(database.sessions, actor)
        data = AdmissionCreateV2(patient_id=patient['id'],type='emergency')
        creator = create_admission_v2
    def worker(i):
        with database.engine.connect() as conn:
            pids.append(conn.scalar(text('SELECT pg_backend_pid()')))
            conn.rollback()
            from sqlalchemy.orm import Session
            with Session(conn, expire_on_commit=False) as s:
                metadata = {}
                barrier.wait(timeout=5)
                result = creator(s, actor=actor, request_id=uuid4(), data=data, idempotency_key=key if same_key else uuid4(), idempotency_metadata=metadata)
                return result, metadata
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(worker, range(2)))
    assert len(set(pids)) == 2
    ids = {r['id'] for r,_ in results}
    assert len(ids) == (1 if same_key else 2)
    assert sorted(m['replayed'] for _,m in results) == ([False,True] if same_key else [False,False])
    with database.sessions() as s:
        for resource_id in ids:
            assert s.scalar(select(func.count()).select_from(AuditEvent).where(AuditEvent.resource_id==resource_id,AuditEvent.action==kind+'.create')) == 1
        assert s.scalar(select(func.count()).select_from(AuditEvent).where(AuditEvent.resource_id.in_(ids),AuditEvent.action==kind+'.replay')) == (1 if same_key else 0)


def test_i07_timeout_5s_rollback_retry_and_scope(database, monkeypatch):
    actor, key = actor_for(database), uuid4()
    with database.sessions() as s:
        evidence = search_patients(s, actor=actor, request_id=uuid4(), filters=SearchFilters(unidentified=True))
    data = PatientCreateV2(identity_status='provisional',search_id=evidence['search_id'])
    with database.sessions() as holder:
        holder.begin()
        reserve(holder, actor, 'v2.patients.create', key, data)
        def competitor():
            started = monotonic()
            with database.sessions() as s, pytest.raises(ApplicationError) as error:
                create_patient_v2(s, actor=actor, request_id=uuid4(), data=data, idempotency_key=key)
            return monotonic()-started, error.value
        with ThreadPoolExecutor(max_workers=1) as pool:
            elapsed, error = pool.submit(competitor).result(timeout=9)
        assert 4.8 <= elapsed < 8 and error.code == 'IDEMPOTENCY_IN_PROGRESS'
        holder.rollback()
    from hospital.administrative import service
    original = service.insert_patient_v2
    def inspect_timeouts(s, *args):
        assert s.scalar(text("SHOW lock_timeout")) == '0'
        assert s.scalar(text("SHOW statement_timeout")) == '2s'
        return original(s, *args)
    monkeypatch.setattr(service,'insert_patient_v2',inspect_timeouts)
    with database.sessions() as s:
        assert create_patient_v2(s, actor=actor, request_id=uuid4(), data=data, idempotency_key=key)['id']


def test_i02_admission_uuid_defaults_and_utc_canonical(client):
    patient = post(client, payload(client), uuid4()).json()
    key = uuid4()
    body = {'patient_id':patient['id'].upper(),'type':'emergency','intake':{'admitted_at':known('2020-01-01T08:30:00-06:00')}}
    first = post(client, body, key, kind='admissions')
    assert first.status_code == 201
    equivalent = {'patient_id':patient['id'],'type':'emergency','intake':{
        'admitted_at':known('2020-01-01T14:30:00Z'), 'origin':{'state':'not_provided','value':None}}}
    repeated = post(client, equivalent, key, kind='admissions')
    assert repeated.status_code == 200 and repeated.json() == first.json()


@pytest.mark.parametrize('invalid', ['missing_resource','both_resources','wrong_operation','missing_fk'])
def test_i05_sql_completed_references_enforced(database, sessions, invalid):
    actor = actor_for(database)
    patient = make_patient(sessions, actor)
    with sessions() as s:
        admission = create_admission_v2(s,actor=actor,request_id=uuid4(),data=AdmissionCreateV2(patient_id=patient['id'],type='emergency'))
    values = {'actor_id':actor.id,'operation':'v2.patients.create','key':uuid4(),'fingerprint':'a'*64,'state':'completed','patient_id':patient['id']}
    if invalid == 'missing_resource': values.pop('patient_id')
    elif invalid == 'both_resources': values['admission_id'] = admission['id']
    elif invalid == 'wrong_operation': values['operation'] = 'v2.admissions.create'
    else: values['patient_id'] = uuid4()
    with sessions() as s, pytest.raises(IntegrityError):
        with s.begin():
            s.add(IdempotencyRecord(**values))
            s.flush()
