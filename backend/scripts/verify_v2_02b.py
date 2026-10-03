"""V2-02B: suite PostgreSQL, preservación, HTTP con respuesta perdida/reinicio.

Sólo datos ficticios. Reinicia el PostgreSQL local del proyecto sin borrar volumen.
El proxy consume la respuesta ya confirmada y cierra sin devolverla al cliente.
"""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import socketserver
import subprocess
import sys
import tempfile
from threading import Event, Thread
from uuid import UUID, uuid4
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend/src'))

import httpx
from sqlalchemy import inspect, select, text
from sqlalchemy.engine import make_url
from hospital.audit.models import AuditEvent
from hospital.core.config import Settings, load_settings
from hospital.core.database import Database
from hospital.idempotency.models import IdempotencyRecord
from hospital.patients.models import Patient
from verify_v2_02a import snapshot, assert_preserved
from verify_phase7 import start_api, stop_api
from verify_phase2 import await_live, compose


def run(*args, env=None, **kwargs):
    return subprocess.run(args, cwd=ROOT, env=env, check=True, **kwargs)


def fresh_database(settings):
    name = 'hospital_v2_02b_validation_' + uuid4().hex
    run('docker','compose','--env-file','backend/.env','exec','-T','postgres','psql','-U','postgres','-d','postgres','-v','ON_ERROR_STOP=1',
        input=f'CREATE DATABASE "{name}" OWNER hospital_dev;\nREVOKE CONNECT ON DATABASE "{name}" FROM PUBLIC;\nGRANT CONNECT ON DATABASE "{name}" TO hospital_dev;\n', text=True)
    url = make_url(settings.database_url.get_secret_value()).set(database=name).render_as_string(hide_password=False)
    env = {**os.environ,'APP_ENV':'production','DEV_IDENTITY_ENABLED':'false','DATABASE_URL':url}
    db = Database(Settings(app_env='production',dev_identity_enabled=False,database_url=url))
    try:
        assert inspect(db.engine).get_table_names() == []
        for args in (('upgrade','head'),('upgrade','head'),('check',)):
            run(sys.executable,'-m','alembic','-c','backend/alembic.ini',*args,env=env)
        with db.engine.connect() as c:
            assert c.scalar(text('SELECT version_num FROM alembic_version')) == '0006'
        return {'name':name,'from_zero':True,'repeated':True,'check':True,'retained':True}
    finally:
        db.dispose()


def lose_committed_response(client, body, headers):
    committed = Event()
    result = {}
    class DropResponse(socketserver.StreamRequestHandler):
        def handle(self):
            self.connection.settimeout(10)
            self.rfile.readline()  # Línea HTTP; no se registra ni conserva.
            length = 0
            while True:
                line = self.rfile.readline()
                if line == b'\r\n': break
                if line.lower().startswith(b'content-length:'):
                    length = int(line.split(b':',1)[1])
            sent = json.loads(self.rfile.read(length))
            try:
                response = client.post('/api/v2/patients', json=sent, headers=headers)
                assert response.status_code == 201
                result.update(response.json())
                # Uvicorn sólo devuelve éxito después del commit del servicio.
                committed.set()
            except Exception:
                result['failed'] = True
            # No escribir la respuesta: el cliente pierde el resultado confirmado.
    with socketserver.TCPServer(('127.0.0.1',0),DropResponse) as proxy:
        worker = Thread(target=proxy.handle_request)
        worker.start()
        try:
            with httpx.Client(trust_env=False, timeout=15) as downstream:
                try:
                    downstream.post(f'http://127.0.0.1:{proxy.server_address[1]}/api/v2/patients',json=body)
                    raise AssertionError('La respuesta debía perderse')
                except httpx.RemoteProtocolError:
                    pass
        finally:
            worker.join(timeout=15)
        assert not worker.is_alive() and committed.is_set() and 'failed' not in result
    return result


def http_probe():
    db = Database(Settings(app_env='test'))
    stopped = False
    with tempfile.TemporaryFile(mode='w+') as logs:
        process, client = start_api(True, logs)
        try:
            await_live(client,process)
            key = uuid4()
            headers = {'X-Dev-Actor':'supervisor-demo','Idempotency-Key':str(key)}
            search = client.get('/api/v2/patients',params={'unidentified':True},headers=headers)
            body = {'identity_status':'provisional','is_unidentified':True,'search_id':search.json()['search_id']}
            patient = lose_committed_response(client,body,headers)
            with db.sessions() as s:
                record = s.scalar(select(IdempotencyRecord).where(IdempotencyRecord.key==key))
                assert record.state=='completed' and record.patient_id==UUID(patient['id'])
                assert s.get(Patient,record.patient_id) is not None
                expires = record.expires_at.isoformat().replace('+00:00','Z')
            recovered = client.post('/api/v2/patients',json=body,headers=headers)
            assert recovered.status_code==200 and recovered.json()==patient
            assert recovered.headers['Idempotency-Expires-At']==expires
            episode_key = uuid4()
            episode_headers = {**headers,'Idempotency-Key':str(episode_key)}
            episode_body = {'patient_id':patient['id'],'type':'emergency','intake':{'reason_for_visit':{'state':'known','value':'Motivo ficticio V2-02B'}}}
            episode = client.post('/api/v2/admissions',json=episode_body,headers=episode_headers)
            assert episode.status_code==201 and episode.headers['Location'].startswith('/api/v2/admissions/')
            episode_result = episode.json()
            # API nueva y pool nuevo; luego caída/reinicio real de PostgreSQL.
            client.close()
            stop_api(process)
            process, client = start_api(True,logs)
            await_live(client,process)
            before_restart = snapshot()
            stopped = True
            compose('stop','postgres')
            assert client.get('/api/v1/health/ready').status_code==503
            compose('up','-d','--wait','postgres')
            stopped = False
            assert_preserved(before_restart,snapshot(),exact=True)
            assert client.get('/api/v1/health/ready').status_code==200
            for kind, request_body, request_headers, original in (
                ('patients',body,headers,patient), ('admissions',episode_body,episode_headers,episode_result)):
                response = client.post('/api/v2/'+kind,json=request_body,headers=request_headers)
                assert response.status_code==200 and response.json()==original
                assert response.headers['Idempotency-Replayed']=='true' and response.headers['Cache-Control']=='no-store'
                assert response.headers['Location']==f"/api/v2/{kind}/{original['id']}"
            # Retención por reloj de base; clave vencida permanece reservada tras reinicio.
            with db.sessions.begin() as s:
                s.execute(text("UPDATE idempotency_records SET created_at=transaction_timestamp()-interval '25 hours', expires_at=transaction_timestamp()-interval '1 hour' WHERE key=:key"),{'key':key})
            expired = client.post('/api/v2/patients',json=body,headers=headers)
            assert expired.status_code==409 and expired.json()['error']['code']=='IDEMPOTENCY_EXPIRED'
            # IN_PROGRESS por HTTP: reserva en otra conexión y espera medible 5 s.
            from hospital.idempotency.service import reserve
            from hospital.administrative.schemas import AdmissionCreateV2
            from hospital.authorization.service import Actor
            from hospital.identity.seed import ROLE_PERMISSIONS
            from hospital.identity.models import User
            with db.sessions() as s:
                user = s.scalar(select(User).where(User.actor_key=='supervisor-demo'))
                actor = Actor(user.id,user.actor_key,ROLE_PERMISSIONS[user.actor_key])
            busy_key = uuid4()
            with db.sessions() as holder:
                holder.begin()
                reserve(holder,actor,'v2.admissions.create',busy_key,AdmissionCreateV2(**episode_body))
                from time import monotonic
                started = monotonic()
                busy = client.post('/api/v2/admissions',json=episode_body,headers={**headers,'Idempotency-Key':str(busy_key)})
                elapsed = monotonic()-started
                assert 4.8<=elapsed<8 and busy.status_code==409
                assert busy.json()['error']['code']=='IDEMPOTENCY_IN_PROGRESS' and busy.headers['Retry-After']=='1'
                assert busy.headers['Cache-Control']=='no-store'
                holder.rollback()
            retry = client.post('/api/v2/admissions',json=episode_body,headers={**headers,'Idempotency-Key':str(busy_key)})
            assert retry.status_code==201
            with db.sessions() as s:
                for kind, resource in (('patients',patient),('admissions',episode_result)):
                    events = s.scalars(select(AuditEvent).where(AuditEvent.resource_id==UUID(resource['id']))).all()
                    assert sum(e.action==kind+'.create' for e in events)==1
                    replays = [e for e in events if e.action==kind+'.replay']
                    assert len(replays)==(2 if kind=='patients' else 1)
                    assert all(e.event_metadata=={} for e in replays)
                    assert len({e.request_id for e in events})==len(events)
            return {'lost_response_after_commit':True,'api_restart':True,'postgresql_stop_start':True,
                'rows_sequences_preserved':True,'same_resources':True,'retention_expired_reserved':True,
                'http_in_progress_retry_after':True,'reservation_wait_seconds':round(elapsed,3),
                'one_creation_per_intention':True,'no_store':True,'patient_id':patient['id'],'admission_id':episode_result['id']}
        finally:
            if stopped: compose('up','-d','--wait','postgres')
            client.close()
            stop_api(process)
            db.dispose()
            logs.seek(0)
            output = logs.read()
            assert 'Traceback' not in output
            assert 'Idempotency-Key' not in output and 'Motivo ficticio' not in output
            for url in (Settings().database_url,Settings().test_database_url):
                assert make_url(url.get_secret_value()).password not in output



def migration_from_0005(settings):
    name = 'hospital_v2_02b_upgrade_' + uuid4().hex
    run('docker','compose','--env-file','backend/.env','exec','-T','postgres','psql','-U','postgres','-d','postgres','-v','ON_ERROR_STOP=1',
        input=f'CREATE DATABASE "{name}" OWNER hospital_dev;\nREVOKE CONNECT ON DATABASE "{name}" FROM PUBLIC;\nGRANT CONNECT ON DATABASE "{name}" TO hospital_dev;\n', text=True)
    url = make_url(settings.database_url.get_secret_value()).set(database=name).render_as_string(hide_password=False)
    env = {**os.environ,'APP_ENV':'production','DEV_IDENTITY_ENABLED':'false','DATABASE_URL':url}
    db = Database(Settings(app_env='production',dev_identity_enabled=False,database_url=url))
    try:
        run(sys.executable,'-m','alembic','-c','backend/alembic.ini','upgrade','0005',env=env)
        from hospital.identity.seed import seed_local_identity, ROLE_PERMISSIONS
        from hospital.identity.models import User
        from hospital.authorization.service import Actor
        from hospital.patients.schemas import PatientCreate, SearchFilters
        from hospital.patients.service import create_patient, search_patients
        from hospital.admissions.schemas import AdmissionCreate
        from hospital.admissions.service import create_admission
        from hospital.administrative.schemas import PatientCreateV2, AdmissionCreateV2
        from hospital.administrative.service import create_patient_v2, create_admission_v2
        with db.sessions() as session:
            # Datos de prueba aislados; no se inicia API en modo producción.
            seed_local_identity(session, Settings(app_env='test'))
        with db.sessions() as session:
            user = session.scalar(select(User).where(User.actor_key=='supervisor-demo'))
            actor = Actor(user.id,user.actor_key,ROLE_PERMISSIONS[user.actor_key])
        with db.sessions() as session:
            old_search = search_patients(session,actor=actor,request_id=uuid4(),filters=SearchFilters(unidentified=True))
            old = create_patient(session,actor=actor,request_id=uuid4(),data=PatientCreate(identity_status='provisional',search_id=old_search['search_id']))
            create_admission(session,actor=actor,request_id=uuid4(),data=AdmissionCreate(patient_id=old['id'],type='inpatient'))
            new_search = search_patients(session,actor=actor,request_id=uuid4(),filters=SearchFilters(name='Persona ficticia migración'))
            new = create_patient_v2(session,actor=actor,request_id=uuid4(),data=PatientCreateV2(identity_status='verified',given_names='Persona ficticia migración',
                birth_date='1990-01-01',search_id=new_search['search_id'],
                administrative_profile={'phones':{'state':'known','value':[{'kind':'personal','number':'000 ficticio'}]}},
                verification=[{'field':f,'source_kind':'official_document','source_reference':'Documento ficticio'} for f in ('full_name','birth_date')]))
            create_admission_v2(session,actor=actor,request_id=uuid4(),data=AdmissionCreateV2(patient_id=new['id'],type='emergency',
                intake={'reason_for_visit':{'state':'known','value':'Motivo ficticio migración'}}))
        def local_snapshot():
            with db.engine.connect() as c:
                return {t:sorted(hashlib.sha256(json.dumps(dict(r),sort_keys=True,default=str).encode()).hexdigest()
                    for r in c.execute(text(f'SELECT * FROM "{t}"')).mappings()) for t in inspect(c).get_table_names() if t!='alembic_version'}, \
                    dict(c.execute(text("SELECT sequencename,last_value FROM pg_sequences WHERE schemaname='public'")).all())
        before_rows, before_sequences = local_snapshot()
        for args in (('upgrade','head'),('upgrade','head'),('check',)):
            run(sys.executable,'-m','alembic','-c','backend/alembic.ini',*args,env=env)
        after_rows, after_sequences = local_snapshot()
        assert all(after_rows[t]==rows for t,rows in before_rows.items())
        assert before_sequences==after_sequences and after_rows['idempotency_records']==[]
        return {'name':name,'from':'0005','to':'0006','v1_v2_data':True,'all_previous_row_hashes_equal':True,
                'sequences_equal':True,'repeated_upgrade_check':True,'retained':True}
    finally:
        db.dispose()

def main():
    settings = load_settings()
    if '--migration-only' in sys.argv:
        result = migration_from_0005(settings)
        target = ROOT/'docs/evidencia/v2-02b-resultados.json'
        report = json.loads(target.read_text())
        report['upgrade_from_0005'] = result
        target.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
        print('Migración 0005 → 0006 con datos V1/V2 comprobada.')
        return
    assert not settings.dev_identity_enabled and settings.app_env in {'development','test'}
    before = snapshot()
    config = ROOT/'backend/.env'
    digest = hashlib.sha256(config.read_bytes()).hexdigest()
    for _ in range(2): run(sys.executable,'backend/scripts/prepare_local.py')
    assert_preserved(before,snapshot(),exact=True)
    assert digest==hashlib.sha256(config.read_bytes()).hexdigest() and config.stat().st_mode & 0o777==0o600
    report = {'phase':'V2-02B','date_utc':datetime.now(timezone.utc).isoformat(),'head':'0006',
              'preparation_runs':2,'config_preserved':True,'previous_rows_preserved':True}
    report['fresh_database'] = fresh_database(settings)
    report['upgrade_from_0005'] = migration_from_0005(settings)
    with tempfile.TemporaryDirectory(prefix='reimbow-v2-02b-') as directory:
        junit = Path(directory)/'pytest.xml'
        run(sys.executable,'-m','pytest','-q','backend/tests','-c','backend/pyproject.toml','--tb=short','--junitxml',str(junit))
        suite = ET.parse(junit).getroot().find('testsuite')
        report['pytest'] = {k:int(suite.attrib.get(k,'0')) for k in ('tests','failures','errors','skipped')}
        assert all(report['pytest'][k]==0 for k in ('failures','errors','skipped'))
    # Preservación antes de modificar fechas de los registros ficticios nuevos.
    assert_preserved(before,snapshot())
    report['http'] = http_probe()
    report['acceptance_cases'] = [f'I{i:02d}' for i in range(1,14)]+['A09','R01']
    report['default_identity_enabled'] = load_settings().dev_identity_enabled
    report['temporary_api_stopped'] = True
    report['limits'] = ['Sin frontend/navegador; A10 pendiente de V2-05/06', 'Sólo demostración local con datos ficticios']
    (ROOT/'docs/evidencia/v2-02b-resultados.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
    print('V2-02B verificada: docs/evidencia/v2-02b-resultados.json')


if __name__=='__main__': main()
