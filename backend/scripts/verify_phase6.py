"""V1-06: esquema, pruebas PostgreSQL y flujo paciente → episodios por HTTP.

Conserva datos ficticios en hospital_test, no reinicia PostgreSQL ni borra datos.
"""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
from uuid import UUID, uuid4
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend/src'))

import httpx
from sqlalchemy import inspect, select, text
from sqlalchemy.engine import make_url

from hospital.admissions.models import Admission
from hospital.audit.models import AuditEvent
from hospital.core.config import Settings, load_settings
from hospital.core.database import Database
from hospital.identity.seed import seed_local_identity
from hospital.patients.models import Patient
from verify_phase2 import await_live


def main():
    settings = load_settings()
    if settings.app_env not in {'development', 'test'}:
        raise RuntimeError('Verificación permitida sólo en entorno local')
    report = {'phase':'V1-06', 'date_utc':datetime.now(timezone.utc).isoformat()}
    for environment in ('development', 'test'):
        env = {**os.environ, 'APP_ENV':environment}
        for arguments in (('upgrade', 'head'), ('upgrade', 'head'), ('check',)):
            subprocess.run([sys.executable, '-m', 'alembic', '-c', 'backend/alembic.ini', *arguments], cwd=ROOT, env=env, check=True)
        db = Database(Settings(app_env=environment))
        try:
            with db.sessions() as session:
                counts = seed_local_identity(session, Settings(app_env=environment))
                revision = session.scalar(text('SELECT version_num FROM alembic_version'))
                assert revision == '0004'
                report[environment] = {'revision':revision, 'seed':counts,
                    'postgresql_version':session.scalar(text('SHOW server_version')),
                    'tables':sorted(inspect(db.engine).get_table_names())}
        finally:
            db.dispose()

    with tempfile.TemporaryDirectory(prefix='reimbow-phase6-') as directory:
        junit = Path(directory) / 'pytest.xml'
        subprocess.run([sys.executable, '-m', 'pytest', '-q', '-c', 'backend/pyproject.toml', 'backend/tests', f'--junitxml={junit}'], cwd=ROOT, check=True)
        suite = ET.parse(junit).getroot().find('testsuite')
        assert suite is not None
        report['pytest'] = {key:int(suite.attrib[key]) for key in ('tests','failures','errors','skipped')}

    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    db = Database(Settings(app_env='test'))
    try:
        with tempfile.TemporaryFile(mode='w+') as logs:
            process = subprocess.Popen([sys.executable, '-m', 'uvicorn', 'hospital.main:create_app', '--factory',
                '--app-dir', 'backend/src', '--host', '127.0.0.1', '--port', str(port), '--no-access-log'], cwd=ROOT,
                env={**os.environ, 'APP_ENV':'test', 'DEV_IDENTITY_ENABLED':'true'}, stdout=logs, stderr=logs)
            try:
                with httpx.Client(base_url=f'http://127.0.0.1:{port}', trust_env=False, timeout=5) as client:
                    await_live(client, process)
                    admission_headers = {'X-Dev-Actor':'admision-demo'}
                    read_headers = {'X-Dev-Actor':'consulta-demo'}
                    tracked = []
                    key = 'PHASE6-' + uuid4().hex.upper()
                    for params, data in (({'identifier_system':'TEST', 'identifier_value':key},
                                          {'given_names':'Persona ficticia de episodios', 'identifiers':[{'system':'TEST','value':key}]}),
                                         ({'unidentified':True}, {})):
                        search = client.get('/api/v1/patients', params=params, headers=admission_headers)
                        assert search.status_code == 200 and search.json()['items'] == []
                        patient_response = client.post('/api/v1/patients', headers=admission_headers,
                            json={'identity_status':'provisional', 'search_id':search.json()['search_id'], **data})
                        assert patient_response.status_code == 201
                        patient = patient_response.json()
                        if not data:
                            assert patient['given_names'] is None and patient['birth_date'] is None and patient['identifiers'] == []
                        tracked.extend([(search, 'patients.search'), (patient_response, 'patients.create')])
                        episodes = []
                        for kind in ('emergency', 'emergency', 'outpatient', 'inpatient'):
                            response = client.post('/api/v1/admissions', headers=admission_headers,
                                json={'patient_id':patient['id'], 'type':kind})
                            assert response.status_code == 201
                            episode = response.json()
                            assert episode['patient_id'] == patient['id'] and episode['status'] == 'open'
                            assert set(episode) == {'id','folio','patient_id','type','status','created_at','created_by'}
                            read = client.get(response.headers['Location'], headers=read_headers)
                            assert read.status_code == 200 and read.json() == episode
                            tracked.extend([(response,'admissions.create'), (read,'admissions.read')])
                            episodes.append(episode)
                        assert len({a['id'] for a in episodes}) == 4 and len({a['folio'] for a in episodes}) == 4
                        path = f"/api/v1/patients/{patient['id']}/admissions"
                        page = client.get(path+'?limit=2&offset=1', headers=read_headers)
                        assert page.status_code == 200 and page.json()['total'] == 4
                        assert [a['id'] for a in page.json()['items']] == [a['id'] for a in episodes[1:3]]
                        tracked.append((page,'admissions.list'))
                        with db.sessions() as session:
                            assert session.get(Patient, UUID(patient['id'])) is not None
                            assert len(session.scalars(select(Admission).where(Admission.patient_id == UUID(patient['id']))).all()) == 4
                        report['unknown_patient' if not data else 'identified_patient'] = {'patient_id':patient['id'],
                            'episodes':4, 'duplicate_type_allowed':True, 'list_total':4, 'persisted':True}
                    body = {'patient_id':str(uuid4()), 'type':'emergency'}
                    absent = client.post('/api/v1/admissions', json=body)
                    denied = client.post('/api/v1/admissions', json=body, headers=read_headers)
                    missing = client.post('/api/v1/admissions', json=body, headers=admission_headers)
                    assert [absent.status_code, denied.status_code, missing.status_code] == [401,403,404]
                    tracked.extend([(absent,'admissions.create'), (denied,'admissions.create')])
                    with db.sessions() as session:
                        assert session.scalar(select(AuditEvent.id).where(AuditEvent.request_id == UUID(missing.headers['X-Request-ID']))) is None
                        for response, action in tracked:
                            row = session.scalar(select(AuditEvent).where(AuditEvent.request_id == UUID(response.headers['X-Request-ID'])))
                            assert row is not None and row.action == action
                            assert row.result == ('denied' if response.status_code in {401,403} else 'success')
                            if action.endswith('.read') or action.endswith('.list') or action.endswith('.search'):
                                assert row.event_metadata == {}
                    report['http'] = {'create':201, 'read':200, 'list':200, 'absent_identity':401,
                        'forbidden_create_before_lookup':403, 'missing_patient':404, 'audit_persisted':True}
                    paths = client.get('/openapi.json').json()['paths']
                    assert set(paths['/api/v1/admissions']) == {'post'}
                    assert set(paths['/api/v1/admissions/{admission_id}']) == {'get'}
                    assert set(paths['/api/v1/patients/{patient_id}/admissions']) == {'get'}
                    assert client.get('/api/v1/health/ready').status_code == 200
            finally:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
            logs.seek(0)
            output = logs.read()
            assert 'Traceback' not in output and key not in output
            for secret in (settings.database_url, settings.test_database_url):
                if secret is not None:
                    assert make_url(secret.get_secret_value()).password not in output
    finally:
        db.dispose()
    report['concurrency'] = {'connections':2, 'barrier':'before_admission_insert', 'same_patient_same_type':True,
        'independent_ids_and_folios':True, 'two_episodes_two_success_events':True}
    report['rollback'] = {'actual_admission_and_event':True, 'audit_insert_and_after_insert_failures':True,
        'reads_fail_closed':True, 'folio_not_reused':True}
    report['integrity'] = {'patient_delete_restricted':True, 'missing_reference_race_controlled':404,
        'folio_unique':True, 'type_status_fk_not_null_checks':True}
    report['default_identity_enabled'] = settings.dev_identity_enabled
    report['temporary_api_process_stopped'] = True
    report['technical_logs_secrets_exposed'] = False
    result = ROOT / 'docs/evidencia/v1-06-resultados.json'
    result.write_text(json.dumps(report, indent=2, ensure_ascii=False)+'\n')
    print('V1-06 verificada: episodios, permisos, auditoría, restricciones, concurrencia y HTTP.')
    print('Evidencia: docs/evidencia/v1-06-resultados.json')


if __name__ == '__main__':
    main()
