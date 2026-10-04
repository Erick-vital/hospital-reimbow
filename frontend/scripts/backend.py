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
from hospital.identity.seed import ROLE_PERMISSIONS, seed_local_identity
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
            seed_local_identity(session, settings)
        with db.sessions() as session:
            assert session.scalar(text('SELECT current_database()'))=='hospital_test'
            assert session.scalar(text('SELECT version_num FROM alembic_version'))=='0007'
            user=session.scalar(select(User).where(User.actor_key=='supervisor-demo',User.status=='active'))
            assert user is not None
            actor=Actor(user.id,user.actor_key,ROLE_PERMISSIONS[user.actor_key])
        denied_key='v203-sin-permisos-'+uuid4().hex
        with db.sessions.begin() as session:
            session.add(User(actor_key=denied_key,provider='development',subject=denied_key))
        patients=[]
        test_identifier='V204-'+uuid4().hex.upper()
        for label in ('Alfa','Beta','Gamma','Delta','Epsilon','Zeta','Eta','Álvarez_%'):
            with db.sessions() as session:
                name='Persona ficticia navegador '+label
                search=search_patients(session,actor=actor,request_id=uuid4(),filters=SearchFilters(name=name, **({'identifier_system':'TEST','identifier_value':test_identifier} if label=='Alfa' else {})))
                patient=create_patient_v2(session,actor=actor,request_id=uuid4(),data=PatientCreateV2(
                    identity_status='verified' if label=='Alfa' else 'provisional',given_names=name,search_id=search['search_id'],
                    identifiers=[{'system':'TEST','value':test_identifier}] if label=='Alfa' else [],
                    verification=[{'field':field,'source_kind':'official_document','source_reference':'Evidencia ficticia no visible V204'} for field in ('full_name','birth_date')] if label=='Alfa' else [],
                    birth_date='1990-01-01',administrative_profile={'nationality':{'state':'known','value':'Ficticia'},
                        'registered_sex':{'state':'unknown'},
                        'phones':{'state':'known','value':[{'kind':'personal','number':'5550002040'},{'kind':'work','number':'5550002041'}]},
                        'addresses':{'state':'known','value':[{'kind':'principal','street':'Calle ficticia 204'},{'kind':'temporary','municipality':'Municipio ficticio 204'}]},
                        'emergency_contacts':{'state':'known','value':[{'name':'Contacto ficticio 204','phone':{'state':'not_provided'},'relationship':{'state':'not_applicable'}}]}}))
                patients.append(patient)
        with db.sessions() as session:
            episode=create_admission_v2(session,actor=actor,request_id=uuid4(),data=AdmissionCreateV2(patient_id=patients[0]['id'],type='emergency',intake={
                'admitted_at':{'state':'known','value':'2026-01-01T12:00:00+00:00'},
                'origin':{'state':'unknown'},'reason_for_visit':{'state':'known','value':'Motivo ficticio 204'}}))
        for _ in range(5):
            with db.sessions() as session:
                create_admission_v2(session,actor=actor,request_id=uuid4(),data=AdmissionCreateV2(patient_id=patients[0]['id'],type='emergency'))
        with db.sessions() as session:
            search=search_patients(session,actor=actor,request_id=uuid4(),filters=SearchFilters(unidentified=True))
            unknown=create_patient_v2(session,actor=actor,request_id=uuid4(),data=PatientCreateV2(identity_status='provisional',is_unidentified=True,search_id=search['search_id'],
                unidentified_description={'estimated_age':{'state':'known','value':{'min_years':30,'max_years':40}},
                    'apparent_sex':{'state':'unknown'},'identifying_features':{'state':'known','value':'Descripción ficticia 204'}}))
        from hospital.patients.schemas import PatientCreate
        from hospital.patients.service import create_patient
        with db.sessions() as session:
            legacy_name='Persona ficticia anterior 204'
            search=search_patients(session,actor=actor,request_id=uuid4(),filters=SearchFilters(name=legacy_name))
            legacy=create_patient(session,actor=actor,request_id=uuid4(),data=PatientCreate(identity_status='verified',given_names=legacy_name,search_id=search['search_id']))
        with db.sessions() as session:
            clinical_second=create_admission_v2(session,actor=actor,request_id=uuid4(),data=AdmissionCreateV2(patient_id=patients[2]['id'],type='emergency'))
        from hospital.administrative.models import Site, Service
        with db.sessions() as session:
            site = session.scalar(select(Site).where(Site.active.is_(True)))
            service = session.scalar(select(Service).where(Service.site_id == site.id, Service.active.is_(True)))
            site_id, service_id = site.id, service.id
        with db.sessions() as session:
            clinical_outpatient=create_admission_v2(session,actor=actor,request_id=uuid4(),data=AdmissionCreateV2(patient_id=patients[0]['id'],type='outpatient',intake={
                'admitted_at':{'state':'known','value':'2026-01-02T12:00:00Z'},
                'site_id':{'state':'known','value':site_id},'service_id':{'state':'known','value':service_id}}))
        # Sólo referencias ficticias para pruebas; sin cuerpos ni configuración.
        print(json.dumps({'patient_id':str(patients[0]['id']),'second_patient_id':str(patients[1]['id']),
                          'clinical_second_patient_id':str(patients[2]['id']),'clinical_second_episode_id':str(clinical_second['id']),'clinical_second_patient_folio':patients[2]['folio'],
                          'clinical_outpatient_id':str(clinical_outpatient['id']),'clinical_site_id':str(site_id),'clinical_service_id':str(service_id),
                          'patient_folio':patients[0]['folio'],'admission_id':str(episode['id']),
                          'admission_folio':episode['folio'],'denied_actor':denied_key, 'test_identifier':test_identifier,
                          'unknown_id':str(unknown['id']),'unknown_folio':unknown['folio'],'legacy_id':str(legacy['id'])}))
    finally:
        db.dispose()


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--serve',type=int)
    parser.add_argument('--demo',choices=('true','false'),default='true')
    parser.add_argument('--expire-search', type=str)
    parser.add_argument('--expire-key', type=str)
    parser.add_argument('--unavailable-db-port', type=int)
    args=parser.parse_args()
    settings=settings_for_test()
    if args.expire_key is not None:
        from uuid import UUID
        key = UUID(args.expire_key)
        assert key.version == 4
        db = Database(settings)
        try:
            with db.sessions.begin() as session:
                assert session.scalar(text('SELECT current_database()')) == 'hospital_test'
                changed = session.execute(text("UPDATE idempotency_records SET created_at = transaction_timestamp() - interval '25 hours', expires_at = transaction_timestamp() - interval '1 hour' WHERE key = :key AND operation = 'v2.admissions.create' AND created_at > clock_timestamp() - interval '2 minutes'"), {'key': key})
                assert changed.rowcount == 1
        finally:
            db.dispose()
    elif args.expire_search is not None:
        from uuid import UUID
        search_id = UUID(args.expire_search)
        db = Database(settings)
        try:
            with db.sessions.begin() as session:
                assert session.scalar(text('SELECT current_database()')) == 'hospital_test'
                changed = session.execute(text("UPDATE patient_searches SET created_at = clock_timestamp() - interval '16 minutes', expires_at = clock_timestamp() - interval '1 second' WHERE id = :id AND created_at > clock_timestamp() - interval '2 minutes'"), {'id': search_id})
                assert changed.rowcount == 1
        finally:
            db.dispose()
    elif args.serve is not None:
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
        if args.unavailable_db_port is not None:
            from sqlalchemy.engine import make_url
            assert 1024 <= args.unavailable_db_port <= 65535
            # API propia apuntando a un puerto loopback reservado sin PostgreSQL;
            # ninguna modificación al servicio/base compartidos ni al .env.
            url = make_url(settings.connection_url).set(port=args.unavailable_db_port)
            api_settings=Settings(app_env='test',dev_identity_enabled=True,
                test_database_url=url.render_as_string(hide_password=False))
        uvicorn.run(create_app(api_settings),host='127.0.0.1',port=args.serve,access_log=False,log_level='warning')
    else:
        fixtures(settings)


if __name__=='__main__':
    try:
        main()
    except Exception:
        sys.stderr.write('No fue posible preparar hospital_test; revise PostgreSQL y la configuración local.\n')
        sys.exit(1)
