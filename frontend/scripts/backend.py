"""API/fixtures de navegador exclusivamente en hospital_test; sin secretos en salida."""
import argparse
import json
from pathlib import Path
import sys
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'backend/src'))

from sqlalchemy import select, text
from sqlalchemy.engine import make_url
from hospital.core.config import Settings
from hospital.core.database import Database
from hospital.identity.models import User
from hospital.identity.seed import ROLE_PERMISSIONS
from hospital.authorization.service import Actor


def settings_for_test():
    settings = Settings(app_env='test',dev_identity_enabled=False)
    assert make_url(settings.connection_url).database=='hospital_test'
    assert make_url(settings.connection_url).username != make_url(settings.database_url.get_secret_value()).username
    return settings


def fixtures(settings):
    from hospital.administrative.schemas import PatientCreateV2, AdmissionCreateV2
    from hospital.administrative.service import create_patient_v2, create_admission_v2
    from hospital.patients.schemas import SearchFilters
    from hospital.patients.service import search_patients
    db = Database(settings)
    try:
        with db.sessions() as session:
            assert session.scalar(text('SELECT current_database()'))=='hospital_test'
            assert session.scalar(text('SELECT version_num FROM alembic_version'))=='0006'
            user=session.scalar(select(User).where(User.actor_key=='supervisor-demo',User.status=='active'))
            assert user is not None
            actor=Actor(user.id,user.actor_key,ROLE_PERMISSIONS[user.actor_key])
        denied_key='v203-sin-permisos-'+uuid4().hex
        with db.sessions.begin() as session:
            session.add(User(actor_key=denied_key,provider='development',subject=denied_key))
        patients=[]
        for label in ('Alfa','Beta'):
            with db.sessions() as session:
                name='Persona ficticia navegador '+label
                search=search_patients(session,actor=actor,request_id=uuid4(),filters=SearchFilters(name=name))
                patient=create_patient_v2(session,actor=actor,request_id=uuid4(),data=PatientCreateV2(
                    identity_status='provisional',given_names=name,search_id=search['search_id'],
                    birth_date='1990-01-01',administrative_profile={'nationality':{'state':'known','value':'Ficticia'}}))
                patients.append(patient)
        with db.sessions() as session:
            episode=create_admission_v2(session,actor=actor,request_id=uuid4(),data=AdmissionCreateV2(patient_id=patients[0]['id'],type='emergency'))
        # Sólo referencias ficticias para pruebas; sin cuerpos ni configuración.
        print(json.dumps({'patient_id':str(patients[0]['id']),'second_patient_id':str(patients[1]['id']),
                          'patient_folio':patients[0]['folio'],'admission_id':str(episode['id']),
                          'admission_folio':episode['folio'],'denied_actor':denied_key}))
    finally:
        db.dispose()


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--serve',type=int)
    parser.add_argument('--demo',choices=('true','false'),default='true')
    args=parser.parse_args()
    settings=settings_for_test()
    if args.serve is not None:
        assert 1024<=args.serve<=65535
        db=Database(settings)
        try:
            with db.sessions() as session:
                assert session.scalar(text('SELECT current_database()'))=='hospital_test'
        finally:
            db.dispose()
        import uvicorn
        from hospital.main import create_app
        api_settings=Settings(app_env='test',dev_identity_enabled=args.demo=='true')
        uvicorn.run(create_app(api_settings),host='127.0.0.1',port=args.serve,access_log=False,log_level='warning')
    else:
        fixtures(settings)


if __name__=='__main__':
    try:
        main()
    except Exception:
        sys.stderr.write('No fue posible preparar hospital_test; revise PostgreSQL y la configuración local.\n')
        sys.exit(1)
