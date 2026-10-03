"""V2-05: registro, ingreso, auditoría y reintentos de UI sobre PostgreSQL.

Conserva configuración y filas anteriores. Las fixtures nuevas son ficticias en
hospital_test. Chromium debe estar instalado localmente según desarrollo-v2.md.
"""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'backend/src'))

from hospital.core.config import load_settings
from verify_v2_02a import snapshot, assert_preserved


def run(*args,env=None):
    subprocess.run(args,cwd=ROOT,env=env,check=True)


def main():
    settings=load_settings()
    assert settings.app_env in {'development','test'} and not settings.dev_identity_enabled
    before=snapshot()
    configuration=ROOT/'backend/.env'
    digest=hashlib.sha256(configuration.read_bytes()).hexdigest()
    lock=ROOT/'frontend/package-lock.json'
    lock_hash=hashlib.sha256(lock.read_bytes()).hexdigest()
    run('npm','--prefix','frontend','run','typecheck')
    for enabled in ('false','true'):
        run('npm','--prefix','frontend','run','build',env={**os.environ,'VITE_DEMO_IDENTITY':enabled})
        scripts=list((ROOT/'frontend/dist/assets').glob('*.js'))
        assert scripts and not any('DemoSelector' in p.name for p in scripts)
        bundled='\n'.join(p.read_text() for p in scripts)
        for value in ('Actor de demostración','admision-demo','supervisor-demo','X-Dev-Actor',
                      settings.database_url.get_secret_value(), settings.test_database_url.get_secret_value()):
            assert value not in bundled
        # Tampoco publicar contraseñas aisladas de las URLs de configuración.
        from sqlalchemy.engine import make_url
        for secret in (settings.database_url,settings.test_database_url):
            assert make_url(secret.get_secret_value()).password not in bundled
    report={'phase':'V2-05','date_utc':datetime.now(timezone.utc).isoformat(),
            'lock_sha256':lock_hash,'typecheck':True,'build_demo_false':True,'build_demo_true':True,
            'demo_selector_actor_headers_absent_from_build':True,'credentials_absent_from_build':True}
    run('npm','--prefix','frontend','run','test:e2e',env={**os.environ,'V2_CAPTURE_WRITE':'true'})
    report['browser']=json.loads((ROOT/'frontend/.cache/e2e-result.json').read_text())
    assert report['browser']['status']=='passed' and report['browser']['total']>=39
    assert report['browser']['services_stopped']
    assert all(case['status']=='passed' for case in report['browser']['cases'])
    with tempfile.TemporaryDirectory(prefix='reimbow-v2-05-') as directory:
        junit=Path(directory)/'pytest.xml'
        run(sys.executable,'-m','pytest','-q','backend/tests','-c','backend/pyproject.toml','--tb=short','--junitxml',str(junit))
        suite=ET.parse(junit).getroot().find('testsuite')
        report['backend_pytest']={k:int(suite.attrib.get(k,'0')) for k in ('tests','failures','errors','skipped')}
        assert all(report['backend_pytest'][k]==0 for k in ('failures','errors','skipped'))
    assert lock_hash==hashlib.sha256(lock.read_bytes()).hexdigest()
    assert_preserved(before,snapshot())
    assert digest==hashlib.sha256(configuration.read_bytes()).hexdigest() and configuration.stat().st_mode & 0o777==0o600
    assert not load_settings().dev_identity_enabled
    report.update(lock_preserved=True,previous_rows_preserved=True,configuration_preserved=True,default_backend_identity_enabled=False)
    report['versions']={name:data['version'] for name,data in json.loads(lock.read_text())['packages'].items()
        if name in {'node_modules/react','node_modules/react-dom','node_modules/vite','node_modules/typescript','node_modules/react-router','node_modules/@playwright/test'}}
    report['acceptance']=['V2-05','F01–F05 (recorrido ampliado)','F06/F07 (altas y desconocido)', 'F09 (reintento UI tras commit)','F08 (409/422 y búsqueda vencida)','F11 (auditoría y replay)','A07 (permisos UI/directos)','A10 (búsqueda/evidencia/borrador)']
    report['limits']=['V2-06 pendiente: cierre de recuperación, concurrencia adicional UI, base caída y revisión funcional M2-03',
        'pageshow persisted comprobado con evento de ciclo; sin afirmar restauración bfcache real',
        'Capturas/revisión técnica no sustituyen M2-01/02/03 ni aceptación clínica']
    (ROOT/'docs/evidencia/v2-05-resultados.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
    print('V2-05 verificada: docs/evidencia/v2-05-resultados.json')


if __name__=='__main__': main()
