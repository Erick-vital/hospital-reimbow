"""V2-02A: preservación, migración nueva/repetida, pruebas y HTTP real.

No borra datos. Guarda sólo hashes/conteos de la base previa, nunca demografía.
--baseline-only captura 0004 antes del primer upgrade; --baseline permite comprobar
ese punto de partida después. Sin opción, toma la base existente como referencia.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from uuid import UUID, uuid4
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend/src'))

from sqlalchemy import inspect, select, text
from sqlalchemy.engine import make_url

from hospital.administrative.schemas import AdmissionCreateV2, PatientCreateV2
from hospital.administrative.service import create_admission_v2, create_patient_v2
from hospital.audit.models import AuditEvent
from hospital.authorization.service import Actor
from hospital.core.config import Settings, load_settings
from hospital.core.database import Database
from hospital.identity.models import User
from hospital.identity.seed import ROLE_PERMISSIONS
from hospital.patients.schemas import SearchFilters
from hospital.patients.service import search_patients
from verify_phase7 import start_api, stop_api
from verify_phase2 import await_live

def run(*args, env=None, **kwargs):
    return subprocess.run(args, cwd=ROOT, env=env, check=True, **kwargs)


def snapshot():
    result = {}
    for environment in ('development', 'test'):
        db = Database(Settings(app_env=environment))
        try:
            with db.engine.connect() as c:
                rows = {}
                for table in sorted(set(inspect(c).get_table_names()) - {'alembic_version'}):
                    # Hash por fila permite conservar el conjunto previo aunque
                    # pruebas posteriores agreguen filas ficticias legítimas.
                    rows[table] = sorted(hashlib.sha256(json.dumps(dict(r), sort_keys=True, default=str).encode()).hexdigest()
                                         for r in c.execute(text(f'SELECT * FROM "{table}"')).mappings())
                sequences = dict(c.execute(text("SELECT sequencename,last_value FROM pg_sequences WHERE schemaname='public'")).all())
                result[environment] = {'rows': rows, 'sequences': sequences,
                    'revision': c.scalar(text('SELECT version_num FROM alembic_version'))}
        finally:
            db.dispose()
    return result


def assert_preserved(before, after, exact=False):
    for environment, data in before.items():
        for table, hashes in data['rows'].items():
            assert set(hashes).issubset(after[environment]['rows'][table]), (environment, table)
            if exact:
                assert hashes == after[environment]['rows'][table]
        for name, value in data['sequences'].items():
            new = after[environment]['sequences'][name]
            assert new == value if exact else value is None or new >= value


def fresh_database(settings):
    name = 'hospital_v2_validation_' + uuid4().hex
    sql = (f'CREATE DATABASE "{name}" OWNER hospital_dev;\n'
           f'REVOKE CONNECT ON DATABASE "{name}" FROM PUBLIC;\n'
           f'GRANT CONNECT ON DATABASE "{name}" TO hospital_dev;\n')
    run('docker', 'compose', '--env-file', 'backend/.env', 'exec', '-T', 'postgres',
        'psql', '-U', 'postgres', '-d', 'postgres', '-v', 'ON_ERROR_STOP=1', input=sql, text=True)
    url = make_url(settings.database_url.get_secret_value()).set(database=name).render_as_string(hide_password=False)
    # Configuración de migración aislada, sin identidad simulada ni API productiva.
    env = {**os.environ, 'APP_ENV': 'production', 'DEV_IDENTITY_ENABLED': 'false', 'DATABASE_URL': url}
    db = Database(Settings(app_env='production', dev_identity_enabled=False, database_url=url))
    try:
        assert inspect(db.engine).get_table_names() == []
        for args in (('upgrade', 'head'), ('upgrade', 'head'), ('check',)):
            run(sys.executable, '-m', 'alembic', '-c', 'backend/alembic.ini', *args, env=env)
        with db.engine.connect() as c:
            assert c.scalar(text('SELECT version_num FROM alembic_version')) == '0005'
        return {'database': name, 'from_zero': True, 'upgrade_repeated': True, 'alembic_check': True, 'retained': True}
    finally:
        db.dispose()


def http_probe():
    db = Database(Settings(app_env='test'))
    try:
        with db.sessions() as s:
            user = s.scalar(select(User).where(User.actor_key == 'supervisor-demo'))
            actor = Actor(user.id, user.actor_key, ROLE_PERMISSIONS[user.actor_key])
        with db.sessions() as s:
            evidence = search_patients(s, actor=actor, request_id=uuid4(), filters=SearchFilters(unidentified=True))
            patient = create_patient_v2(s, actor=actor, request_id=uuid4(), data=PatientCreateV2(
                identity_status='provisional', is_unidentified=True, search_id=evidence['search_id']))
            admission = create_admission_v2(s, actor=actor, request_id=uuid4(), data=AdmissionCreateV2(patient_id=patient['id'], type='emergency'))
            named_search = search_patients(s, actor=actor, request_id=uuid4(), filters=SearchFilters(name='Persona ficticia V2'))
            verified = create_patient_v2(s, actor=actor, request_id=uuid4(), data=PatientCreateV2(
                identity_status='verified', given_names='Persona ficticia V2', birth_date='1990-01-01', search_id=named_search['search_id'],
                administrative_profile={'phones': {'state':'known', 'value':[{'kind':'personal', 'number':'000 ficticio'}]}},
                verification=[{'field': f, 'source_kind':'official_document', 'source_reference':'Documento ficticio observado'}
                              for f in ('full_name','birth_date')]))
        tracked = []
        with tempfile.TemporaryFile(mode='w+') as logs:
            process, client = start_api(True, logs)
            try:
                with client:
                    await_live(client, process)
                    for actor_key in ('supervisor-demo', 'consulta-demo'):
                        headers = {'X-Dev-Actor': actor_key}
                        for path in (f"/patients/{patient['id']}", f"/admissions/{admission['id']}",
                                     f"/patients/{patient['id']}/admissions", f"/patients?folio={patient['folio']}"):
                            response = client.get('/api/v2' + path, headers=headers)
                            assert response.status_code == 200
                            assert response.headers['Cache-Control'] == 'no-store'
                            UUID(response.headers['X-Request-ID'])
                            tracked.append(response)
                            if actor_key == 'consulta-demo':
                                assert all(word not in response.json() for word in ('intake', 'administrative_profile', 'verification'))
                                assert 'reason_for_visit' not in response.text and 'registered_sex' not in response.text
                    headers = {'X-Dev-Actor': 'supervisor-demo'}
                    sites = client.get('/api/v2/catalogs/sites?limit=1', headers=headers)
                    assert sites.status_code == 200 and len(sites.json()['items']) == 1
                    site_id = sites.json()['items'][0]['id']
                    services = client.get('/api/v2/catalogs/services', params={'site_id': site_id}, headers=headers)
                    assert services.status_code == 200 and services.json()['total'] >= 1
                    tracked.extend([sites, services])
                    service_id = services.json()['items'][0]['id']
                    with db.sessions() as s:
                        outpatient = create_admission_v2(s, actor=actor, request_id=uuid4(), data=AdmissionCreateV2(
                            patient_id=verified['id'], type='outpatient', intake={
                                'admitted_at':{'state':'known','value':'2020-01-01T08:30:00-06:00'},
                                'site_id':{'state':'known','value':site_id}, 'service_id':{'state':'known','value':service_id}}))
                    verified_read = client.get('/api/v2/patients/' + str(verified['id']), headers=headers)
                    assert verified_read.status_code == 200 and verified_read.json()['verification_quality'] == 'documented'
                    assert len(verified_read.json()['verification']['evidence']) == 2
                    outpatient_read = client.get('/api/v2/admissions/' + str(outpatient['id']), headers=headers)
                    assert outpatient_read.status_code == 200 and outpatient_read.json()['intake']['admitted_at']['value'] == '2020-01-01T14:30:00Z'
                    tracked.extend([verified_read, outpatient_read])
                    denied = client.get('/api/v2/catalogs/sites', headers={'X-Dev-Actor': 'consulta-demo'})
                    absent = client.get('/api/v2/patients/' + str(patient['id']))
                    assert denied.status_code == 403 and absent.status_code == 401
                    tracked.extend([denied, absent])
                    assert client.post('/api/v2/patients', headers=headers, json={}).status_code == 405
                    assert client.post('/api/v2/admissions', headers=headers, json={}).status_code == 404
                    v1 = client.get('/api/v1/patients/' + str(patient['id']), headers=headers)
                    assert v1.status_code == 200 and 'verification_quality' not in v1.json()
            finally:
                stop_api(process)
            logs.seek(0)
            output = logs.read()
            assert 'Traceback' not in output and str(patient['id']) not in output
            for url in (Settings().database_url, Settings().test_database_url):
                assert make_url(url.get_secret_value()).password not in output
        with db.sessions() as s:
            for response in tracked:
                row = s.scalar(select(AuditEvent).where(AuditEvent.request_id == UUID(response.headers['X-Request-ID'])))
                assert row is not None
                assert row.event_metadata == ({} if response.status_code == 200 else {'code': response.json()['error']['code']})
        return {'requests_audited': len(tracked), 'tcp_loopback': True, 'permissions': True, 'no_store': True,
                'post_v2_disabled': True, 'v1_compatible': True, 'api_stopped': True, 'logs_private': True,
                'fictitious_patient_id': str(patient['id']), 'fictitious_admission_id': str(admission['id'])}
    finally:
        db.dispose()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--baseline', type=Path)
    parser.add_argument('--baseline-only', type=Path)
    args = parser.parse_args()
    settings = load_settings()
    assert settings.app_env in {'development', 'test'} and not settings.dev_identity_enabled
    before = snapshot()
    if args.baseline_only:
        args.baseline_only.write_text(json.dumps(before, indent=2) + '\n')
        print('Punto de partida guardado: hashes/conteos, sin demografía.')
        return
    baseline = json.loads(args.baseline.read_text()) if args.baseline else before
    config = ROOT / 'backend/.env'
    config_hash = hashlib.sha256(config.read_bytes()).hexdigest()
    for _ in range(2):
        run(sys.executable, 'backend/scripts/prepare_local.py')
    after = snapshot()
    assert_preserved(baseline, after)
    assert_preserved(before, after, exact=True)
    assert config_hash == hashlib.sha256(config.read_bytes()).hexdigest() and config.stat().st_mode & 0o777 == 0o600
    report = {'phase': 'V2-02A', 'date_utc': datetime.now(timezone.utc).isoformat(),
              'migration': {'before': {e: {'revision': d['revision'], 'counts': {t:len(r) for t,r in d['rows'].items()}, 'sequences':d['sequences']} for e,d in baseline.items()},
                            'head': '0005', 'v1_rows_preserved': True, 'preparation_runs': 2, 'config_preserved': True}}
    report['fresh_database'] = fresh_database(settings)
    with tempfile.TemporaryDirectory(prefix='reimbow-v2-02a-') as directory:
        junit = Path(directory) / 'pytest.xml'
        run(sys.executable, '-m', 'pytest', '-q', 'backend/tests', '-c', 'backend/pyproject.toml', '--junitxml', str(junit))
        suite = ET.parse(junit).getroot().find('testsuite')
        report['pytest'] = {k:int(suite.attrib.get(k, '0')) for k in ('tests', 'failures', 'errors', 'skipped')}
    report['http'] = http_probe()
    assert_preserved(baseline, snapshot())
    report['acceptance_cases'] = ['A01','A02','A03','A04','A05','A06','A07','A08']
    report['limits'] = ['POST V2 pendiente de V2-02B', 'Sin frontend ni validación clínica/productiva']
    report['default_identity_enabled'] = load_settings().dev_identity_enabled
    (ROOT / 'docs/evidencia/v2-02a-resultados.json').write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n')
    print('V2-02A verificada. Evidencia: docs/evidencia/v2-02a-resultados.json')


if __name__ == '__main__':
    main()
