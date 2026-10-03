"""A01–A08: contratos, integridad SQL, atomicidad y lecturas V2/PostgreSQL."""
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy import func, select, text, update
from sqlalchemy.exc import IntegrityError

from hospital.administrative.models import AdmissionIntake, PatientCollectionItem, PatientProfile, Service, Site, Verification, VerificationEvidence
from hospital.administrative.projections import admission_v2_projection
from hospital.administrative.schemas import AdmissionCreateV2, PatientCreateV2
from hospital.administrative.service import create_admission_v2, create_patient_v2, list_catalog
from hospital.admissions.models import Admission
from hospital.admissions.service import read_admission
from hospital.audit.models import AuditEvent
from hospital.core.config import Settings
from hospital.core.errors import ApplicationError
from hospital.identity.seed import seed_local_identity
from hospital.patients.models import Patient
from hospital.patients.schemas import SearchFilters
from hospital.patients.service import search_patients
from test_patients_postgresql import actor_for, client, database, sessions, create as create_v1, headers


def known(value):
    return {'state': 'known', 'value': value}


def verified_data(second='birth_date'):
    data = {'identity_status': 'verified', 'given_names': ' Persona ficticia ', 'family_name': ' Prueba ',
            'verification': [{'field': f, 'source_kind': 'official_document', 'source_reference': 'Documento ficticio observado'}
                             for f in ('full_name', second)]}
    if second == 'birth_date':
        data['birth_date'] = '1990-01-01'
    else:
        data['identifiers'] = [{'system': 'CURP', 'value': 'TEST' + uuid4().hex[:14].upper()}]
    return data


def make_patient(sessions, actor, **data):
    data = PatientCreateV2(**{'identity_status': 'provisional', **data})
    if data.identifiers:
        filters = SearchFilters(identifier_system=data.identifiers[0].system, identifier_value=data.identifiers[0].value)
    elif data.given_names or data.family_name or data.second_family_name:
        from hospital.patients.schemas import full_name
        filters = SearchFilters(name=full_name(data))
    else:
        filters = SearchFilters(unidentified=True)
    with sessions() as session:
        evidence = search_patients(session, actor=actor, request_id=uuid4(), filters=filters)
        data.search_id = evidence['search_id']
        return create_patient_v2(session, actor=actor, request_id=uuid4(), data=data)


@pytest.mark.parametrize('profile', [
    {'registered_sex': known(None)}, {'nationality': {'state': 'unknown', 'value': 'x'}},
    {'nationality': known(' ')}, {'nationality': known('x'*101)},
    {'phones': known([{'kind': 'personal', 'number': '1'}]*11)},
    {'phones': known([{'kind': 'other', 'number': ' '}])},
    {'phones': known([{'kind': 'other', 'number': '1'*41}])},
    {'addresses': known([{'kind': 'principal'}])},
    {'addresses': known([{'kind': 'other', 'country': ' '}])},
    {'addresses': known([{'kind': 'other', 'postal_code': 'x'*21}])},
    {'emergency_contacts': known([{'phone': known('1')}])},
    {'emergency_contacts': known([{'name': 'Ficticio', 'relationship': known(' ')}])},
    {'emergency_contacts': known([{'name': 'Ficticio', 'phone': {'state': 'unknown', 'value': '1'}}])},
    {'email': known('no-scope')},
])
def test_a01_invalid_profiles(profile):
    with pytest.raises(ValidationError):
        PatientCreateV2(identity_status='provisional', administrative_profile=profile)


@pytest.mark.integration
def test_a01_multiple_contacts_foreign_addresses_states_persisted(client, database, sessions):
    actor = actor_for(database)
    profile = {'registered_sex': known('  Declarado  '), 'nationality': known('  Ficticia extranjera '),
        'phones': known([{'kind': 'personal', 'number': ' +44 000 ext 2 '}, {'kind': 'work', 'number': ' 00-00 '}]),
        'addresses': known([{'kind': 'principal', 'country': ' País ficticio ', 'postal_code': 'AB 12'},
                            {'kind': 'temporary', 'references': 'Referencia ficticia'}]),
        'emergency_contacts': known([{'name': '  Contacto ficticio  ', 'relationship': {'state': 'unknown'}, 'phone': known('000')},
                                     {'name': 'Otro contacto ficticio'}])}
    patient = make_patient(sessions, actor, administrative_profile=profile)
    assert patient['administrative_profile']['nationality']['value'] == 'Ficticia extranjera'
    assert patient['administrative_profile']['phones']['value'][0]['number'] == '+44 000 ext 2'
    assert patient['identity_field_states']['birth_date'] == 'not_provided'
    with sessions() as session:
        assert session.scalar(select(func.count()).select_from(PatientCollectionItem).where(PatientCollectionItem.patient_id == patient['id'])) == 6
    response = client.get('/api/v2/patients/' + str(patient['id']), headers=headers())
    assert response.status_code == 200 and response.json()['administrative_profile'] == patient['administrative_profile']
    empty = make_patient(sessions, actor, administrative_profile={'phones': known([]), 'addresses': {'state': 'not_applicable'}})
    assert empty['administrative_profile']['phones'] == known([])
    assert empty['administrative_profile']['addresses'] == {'state': 'not_applicable', 'value': None}


@pytest.mark.parametrize('data', [
    {'is_unidentified': True, 'given_names': 'inventado'}, {'is_unidentified': True, 'birth_date': '1990-01-01'},
    {'is_unidentified': True, 'identifiers': [{'system': 'TEST', 'value': 'NO'}]},
    {'is_unidentified': True, 'unidentified_description': {'estimated_age': known({'min_years': 30, 'max_years': 20})}},
    {'is_unidentified': True, 'unidentified_description': {'estimated_age': known({'min_years': 0, 'max_years': 151})}},
    {'is_unidentified': True, 'unidentified_description': {'estimated_age': known({'min_years': True, 'max_years': 10})}},
    {'unidentified_description': {'apparent_sex': known('Aparente')}},
    {'given_names': 'Ficticio', 'identity_field_states': {'given_names': 'unknown'}},
    {'identity_field_states': {'birth_date': 'known'}},
])
def test_a02_unknown_contradictions(data):
    with pytest.raises(ValidationError):
        PatientCreateV2(identity_status='provisional', **data)


@pytest.mark.integration
def test_a02_explicit_unknown_without_descriptors_and_with_age(client, database, sessions):
    actor = actor_for(database)
    plain = make_patient(sessions, actor, is_unidentified=True)
    rich = make_patient(sessions, actor, is_unidentified=True,
                        administrative_profile={'registered_sex': known('Registrado')},
                        unidentified_description={'apparent_sex': known('Aparente'), 'estimated_age': known({'min_years': 20, 'max_years': 30})})
    assert plain['birth_date'] is None and plain['given_names'] is None and plain['identifiers'] == []
    assert rich['administrative_profile']['registered_sex']['value'] == 'Registrado'
    assert rich['unidentified_description']['apparent_sex']['value'] == 'Aparente'
    page = client.get('/api/v2/patients?unidentified=true', headers=headers())
    assert page.status_code == 200 and page.json()['total'] >= 2
    ids = {item['id'] for item in page.json()['items']}
    assert str(plain['id']) in ids and str(rich['id']) in ids
    assert client.get('/api/v1/patients?unidentified=true', headers=headers()).json()['items'] == []


@pytest.mark.parametrize('change', ['only_name', 'TEST', 'folio', 'duplicate', 'missing_birth', 'missing_curp', 'referred', 'actor', 'date', 'snapshot', 'provisional'])
def test_a03_invalid_verification(change):
    data = verified_data()
    if change == 'only_name': data['verification'] = data['verification'][:1]
    elif change in {'TEST','folio'}: data['verification'][1]['field'] = change
    elif change == 'duplicate': data['verification'].append(data['verification'][0])
    elif change == 'missing_birth': data.pop('birth_date')
    elif change == 'missing_curp': data['verification'][1]['field'] = 'CURP'
    elif change == 'referred': data['verification'][1]['source_kind'] = 'family_report'
    elif change in {'actor','date','snapshot'}: data['verification'][1][change] = str(uuid4())
    elif change == 'provisional': data['identity_status'] = 'provisional'
    with pytest.raises(ValidationError):
        PatientCreateV2(**data)


@pytest.mark.integration
@pytest.mark.parametrize('second', ['birth_date', 'CURP'])
def test_a03_verified_two_identifiers_snapshots_and_server_actor(client, database, sessions, second):
    actor = actor_for(database)
    before = datetime.now(timezone.utc)
    patient = make_patient(sessions, actor, **verified_data(second))
    verification = patient['verification']
    assert patient['verification_quality'] == 'documented' and verification['verified_by'] == actor.id
    assert before <= verification['verified_at'] <= datetime.now(timezone.utc)
    snapshots = {e['field']: e['snapshot'] for e in verification['evidence']}
    assert snapshots['full_name']['given_names'] == 'Persona ficticia'
    assert set(snapshots) == {'full_name', second}
    with sessions.begin() as session:
        session.execute(text('SET CONSTRAINTS ALL IMMEDIATE'))
    assert client.get('/api/v2/patients/' + str(patient['id']), headers=headers()).json()['verification_quality'] == 'documented'
    basic = client.get('/api/v2/patients/' + str(patient['id']), headers=headers('consulta-demo')).json()
    assert basic['verification_quality'] == 'documented' and 'verification' not in basic and 'birth_date' not in basic


@pytest.mark.integration
def test_a04_denied_before_search_or_write(database):
    actor = actor_for(database, 'admision-demo')
    with database.sessions() as session, pytest.raises(ApplicationError) as error:
        create_patient_v2(session, actor=actor, request_id=uuid4(), data=PatientCreateV2(**verified_data()))
    assert error.value.status == 403


@pytest.mark.integration
@pytest.mark.parametrize('failure', ['evidence', 'audit', 'after_audit'])
def test_a04_patient_evidence_and_audit_atomic_rollback(database, monkeypatch, failure):
    from hospital.administrative import service
    actor = actor_for(database)
    data = PatientCreateV2(**verified_data())
    with database.sessions() as session:
        receipt = search_patients(session, actor=actor, request_id=uuid4(), filters=SearchFilters(name='Persona ficticia Prueba'))
    data.search_id = receipt['search_id']
    correlation = uuid4()
    allocated = []
    original = service.record_success
    def fail(session, **kwargs):
        allocated.append(kwargs['resource_id'])
        if failure == 'evidence':
            session.execute(update(VerificationEvidence).where(VerificationEvidence.patient_id == kwargs['resource_id']).values(source_reference=' '))
        elif failure == 'audit':
            original(session, **{**kwargs, 'request_id': None})
        else:
            original(session, **kwargs)
            raise RuntimeError('Fallo ficticio tras auditoría')
    monkeypatch.setattr(service, 'record_success', fail)
    with database.sessions() as session, pytest.raises((IntegrityError, RuntimeError)):
        create_patient_v2(session, actor=actor, request_id=correlation, data=data)
    with database.sessions() as session:
        assert session.get(Patient, allocated[0]) is None
        for model in (PatientProfile, Verification, VerificationEvidence):
            assert session.scalar(select(model).where(model.patient_id == allocated[0])) is None
        assert session.scalar(select(AuditEvent).where(AuditEvent.request_id == correlation)) is None


@pytest.mark.integration
def test_a05_catalog_pagination_access_activity_and_seed(client, database, sessions):
    actor = actor_for(database)
    with sessions() as session:
        sites = session.scalars(select(Site).order_by(Site.code)).all()
        ids = {s.code: s.id for s in sites}
        service = session.scalar(select(Service).where(Service.site_id == sites[0].id))
        service_id = service.id
    first = client.get('/api/v2/catalogs/sites?limit=1', headers=headers()).json()
    second = client.get('/api/v2/catalogs/sites?limit=1&offset=1', headers=headers()).json()
    assert first['total'] >= 2 and first['items'][0]['id'] != second['items'][0]['id']
    assert client.get('/api/v2/catalogs/sites?offset=999', headers=headers()).json()['items'] == []
    assert client.get('/api/v2/catalogs/sites', headers=headers('consulta-demo')).status_code == 403
    assert client.get('/api/v2/catalogs/services', headers=headers()).status_code == 422
    assert client.get('/api/v2/catalogs/services?site_id=' + str(uuid4()), headers=headers()).status_code == 404
    with sessions.begin() as session:
        session.execute(update(Site).where(Site.id == sites[0].id).values(active=False, name='Nombre ficticio conservado'))
        session.execute(update(Service).where(Service.id == service_id).values(active=False))
    for _ in range(2):
        with sessions() as session:
            seed_local_identity(session, Settings(app_env='test'))
    with sessions() as session:
        assert ids == {s.code:s.id for s in session.scalars(select(Site))}
        assert not session.get(Site, sites[0].id).active
        assert session.get(Site, sites[0].id).name == 'Nombre ficticio conservado'
        assert not session.get(Service, service_id).active
    assert client.get('/api/v2/catalogs/services?site_id=' + str(sites[0].id), headers=headers()).status_code == 404


@pytest.mark.parametrize('intake', [{'admitted_at': known('2999-01-01T00:00:00Z')}, {'admitted_at': known('2020-01-01T00:00:00')},
                                     {'admitted_at': known(0)}, {'admitted_at': known('0')},
                                     {'admitted_at': known(None)}, {'service_id': known(str(uuid4()))},
                                     {'origin': known(' ')}, {'reason_for_visit': known('x'*1001)}])
def test_a06_invalid_intake(intake):
    with pytest.raises(ValidationError):
        AdmissionCreateV2(patient_id=uuid4(), type='emergency', intake=intake)


@pytest.mark.parametrize('kind', ['outpatient', 'inpatient'])
def test_a06_non_emergency_requires_intake(kind):
    with pytest.raises(ValidationError):
        AdmissionCreateV2(patient_id=uuid4(), type=kind)


@pytest.mark.integration
def test_a06_emergency_pending_and_clinical_time_utc(client, database, sessions):
    actor = actor_for(database)
    patient = make_patient(sessions, actor, is_unidentified=True)
    with sessions() as session:
        service = session.scalar(select(Service).where(Service.active.is_(True)))
        site_id, service_id = service.site_id, service.id
    with sessions() as session:
        pending = create_admission_v2(session, actor=actor, request_id=uuid4(), data=AdmissionCreateV2(patient_id=patient['id'], type='emergency'))
    assert all(field['state'] == 'not_provided' for field in pending['intake'].values())
    for kind in ('emergency', 'outpatient', 'inpatient'):
        data = AdmissionCreateV2(patient_id=patient['id'], type=kind, intake={
            'admitted_at': known('2020-01-01T08:30:00-06:00'), 'site_id': known(site_id), 'service_id': known(service_id),
            'origin': {'state': 'unknown'}, 'reason_for_visit': known('Motivo ficticio')})
        with sessions() as session:
            result = create_admission_v2(session, actor=actor, request_id=uuid4(), data=data)
        assert datetime.fromisoformat(result['intake']['admitted_at']['value']) == datetime(2020,1,1,14,30,tzinfo=timezone.utc)
        assert result['created_at'] > datetime.fromisoformat(result['intake']['admitted_at']['value'])
        full = client.get('/api/v2/admissions/' + str(result['id']), headers=headers()).json()
        basic = client.get('/api/v2/admissions/' + str(result['id']), headers=headers('consulta-demo')).json()
        assert full['intake']['reason_for_visit']['value'] == 'Motivo ficticio' and 'intake' not in basic
    page = client.get('/api/v2/patients/' + str(patient['id']) + '/admissions?limit=2', headers=headers())
    assert page.status_code == 200 and page.json()['total'] == 4 and len(page.json()['items']) == 2


@pytest.mark.integration
@pytest.mark.parametrize('bad', ['missing', 'inactive_site', 'inactive_service', 'wrong_pair'])
def test_a05_intake_catalog_rejection(database, sessions, bad):
    actor = actor_for(database)
    patient = make_patient(sessions, actor)
    with sessions() as session:
        services = session.scalars(select(Service).order_by(Service.site_id)).all()
        site_id, service_id = services[0].site_id, services[0].id
        other_site = next(s.site_id for s in services if s.site_id != site_id)
    if bad == 'missing': service_id = uuid4()
    elif bad == 'wrong_pair': site_id = other_site
    else:
        with sessions.begin() as session:
            session.execute(update(Site if bad == 'inactive_site' else Service).where(
                (Site.id == site_id) if bad == 'inactive_site' else (Service.id == service_id)).values(active=False))
    with sessions() as session, pytest.raises(ApplicationError) as error:
        create_admission_v2(session, actor=actor, request_id=uuid4(), data=AdmissionCreateV2(patient_id=patient['id'], type='emergency',
            intake={'site_id': known(site_id), 'service_id': known(service_id)}))
    assert error.value.status == 422


@pytest.mark.integration
def test_a07_field_permissions_never_grant_resource_access(client, database, sessions):
    actor = actor_for(database)
    patient = make_patient(sessions, actor, administrative_profile={'nationality': known('Ficticia')})
    basic = client.get('/api/v2/patients/' + str(patient['id']), headers=headers('consulta-demo'))
    assert basic.status_code == 200 and set(basic.json()) == {'id','folio','identity_status','given_names','family_name','second_family_name','verification_quality'}
    only_intake = replace(actor, permissions=frozenset({'admissions.read_intake'}))
    with sessions() as session, pytest.raises(ApplicationError) as error:
        read_admission(session, actor=only_intake, request_id=uuid4(), admission_id=uuid4(), project=admission_v2_projection)
    assert error.value.status == 403
    for path in ('/patients/' + str(uuid4()), '/admissions/' + str(uuid4()), '/catalogs/sites'):
        assert client.get('/api/v2' + path).status_code == 401
    assert client.get('/api/v2/patients/' + str(uuid4()), headers=headers()).status_code == 404
    assert client.get('/api/v2/patients/bad', headers=headers()).status_code == 422


@pytest.mark.integration
def test_a08_v1_declarations_absences_and_responses_unchanged(client, sessions):
    old = create_v1(client, identity_status='verified', given_names='Declaración ficticia V1').json()
    read = client.get('/api/v2/patients/' + old['id'], headers=headers()).json()
    assert read['verification_quality'] == 'legacy_unsubstantiated' and read['verification'] is None
    assert read['is_unidentified'] is None and read['administrative_origin'] == 'legacy'
    assert read['administrative_profile']['nationality']['state'] == 'not_provided'
    episode = client.post('/api/v1/admissions', headers=headers(), json={'patient_id':old['id'], 'type':'inpatient'}).json()
    v2 = client.get('/api/v2/admissions/' + episode['id'], headers=headers()).json()
    assert v2['intake']['admitted_at'] == {'state':'not_provided', 'value':None} and v2['intake_origin'] == 'legacy'
    assert client.get('/api/v1/patients/' + old['id'], headers=headers()).json() == old
    assert client.get('/api/v1/admissions/' + episode['id'], headers=headers()).json() == episode
    with sessions() as session:
        assert session.get(PatientProfile, UUID(old['id'])) is None and session.get(AdmissionIntake, UUID(episode['id'])) is None
    paths = client.get('/openapi.json').json()['paths']
    assert set(paths['/api/v2/patients']) == {'get', 'post'} and 'post' in paths['/api/v2/admissions']


@pytest.mark.integration
@pytest.mark.parametrize('change', ['verification_missing', 'snapshot', 'identity_state', 'unknown_identity', 'collection_state', 'age', 'profile_keys', 'null_state'])
def test_direct_sql_patient_constraints_at_commit(database, sessions, change):
    actor = actor_for(database)
    patient = make_patient(sessions, actor, **verified_data())
    with sessions() as session, pytest.raises(IntegrityError):
        with session.begin():
            profile = session.get(PatientProfile, patient['id'])
            data = deepcopy(profile.data)
            if change == 'verification_missing':
                session.execute(text('DELETE FROM patient_verification_evidence WHERE patient_id=:id AND field=:field'), {'id':patient['id'], 'field':'birth_date'})
            elif change == 'snapshot':
                session.execute(update(VerificationEvidence).where(VerificationEvidence.patient_id == patient['id']).values(snapshot={'bad': 'ficticio'}))
            elif change == 'unknown_identity': profile.is_unidentified = True
            elif change == 'identity_state': data['identity_field_states']['given_names'] = 'unknown'
            elif change == 'collection_state':
                session.add(PatientCollectionItem(patient_id=patient['id'], kind='phones', position=0, data={'kind':'personal','number':'000'}))
            elif change == 'age': data['unidentified_description']['estimated_age'] = known({'min_years':40,'max_years':20})
            elif change == 'profile_keys': data.pop('nationality')
            elif change == 'null_state': data['nationality'] = {'state':None, 'value':'Ficticia'}
            profile.data = data
            session.flush()
            # Los tests usan savepoints: forzar constraint triggers pendientes
            # para comprobar la misma validación que realiza un commit real.
            session.execute(text('SET CONSTRAINTS ALL IMMEDIATE'))


@pytest.mark.integration
@pytest.mark.parametrize('change', ['wrong_pair', 'missing_fk', 'non_emergency', 'time_mismatch', 'state_value', 'future'])
def test_direct_sql_intake_constraints(database, sessions, change):
    actor = actor_for(database)
    patient = make_patient(sessions, actor)
    with sessions() as session:
        episode = create_admission_v2(session, actor=actor, request_id=uuid4(), data=AdmissionCreateV2(patient_id=patient['id'], type='emergency'))
    with sessions() as session, pytest.raises(IntegrityError):
        with session.begin():
            intake = session.get(AdmissionIntake, episode['id'])
            data = deepcopy(intake.data)
            if change in {'wrong_pair','missing_fk'}:
                services = session.scalars(select(Service)).all()
                intake.site_id = services[0].site_id
                intake.service_id = uuid4() if change == 'missing_fk' else next(s.id for s in services if s.site_id != intake.site_id)
                data.update(site_id=known(str(intake.site_id)), service_id=known(str(intake.service_id)))
            elif change == 'non_emergency': session.get(Admission, episode['id']).type = 'inpatient'
            elif change == 'time_mismatch': intake.admitted_at = datetime(2020,1,1,tzinfo=timezone.utc)
            elif change == 'state_value': data['origin'] = {'state':'unknown', 'value':'Ficticia'}
            elif change == 'future':
                intake.admitted_at = datetime.now(timezone.utc) + timedelta(days=1)
                data['admitted_at'] = known(intake.admitted_at.isoformat())
            intake.data = data
            session.flush()
            session.execute(text('SET CONSTRAINTS ALL IMMEDIATE'))


@pytest.mark.integration
def test_sql_cannot_move_verification_evidence_to_another_patient(database, sessions):
    actor = actor_for(database)
    first = make_patient(sessions, actor, **verified_data())
    second = make_patient(sessions, actor, **verified_data('CURP'))
    # La evidencia de nacimiento encajaría en el segundo si se añadiera ese
    # campo: aun así no puede dejar al primero verificado con sólo su nombre.
    with sessions() as session, pytest.raises(IntegrityError):
        with session.begin():
            second_patient = session.get(Patient, second['id'])
            second_patient.birth_date = datetime(1990,1,1).date()
            profile = session.get(PatientProfile, second['id'])
            data = deepcopy(profile.data)
            data['identity_field_states']['birth_date'] = 'known'
            profile.data = data
            session.execute(update(VerificationEvidence).where(VerificationEvidence.patient_id == first['id'],
                VerificationEvidence.field == 'birth_date').values(patient_id=second['id']))
            session.flush()
            session.execute(text('SET CONSTRAINTS ALL IMMEDIATE'))


@pytest.mark.integration
def test_intake_and_catalog_reads_roll_back_on_audit_failure(client, database, sessions, monkeypatch):
    from hospital.administrative import service
    original = service.record_success
    actor = actor_for(database)
    patient = make_patient(sessions, actor)
    ids = []
    def fail(session, **kwargs):
        if kwargs.get('resource_id'): ids.append(kwargs['resource_id'])
        original(session, **{**kwargs, 'request_id':None})
    monkeypatch.setattr(service, 'record_success', fail)
    with sessions() as session, pytest.raises(IntegrityError):
        create_admission_v2(session, actor=actor, request_id=uuid4(), data=AdmissionCreateV2(patient_id=patient['id'], type='emergency'))
    with sessions() as session:
        assert session.get(Admission, ids[0]) is None and session.get(AdmissionIntake, ids[0]) is None
    response = client.get('/api/v2/catalogs/sites', headers=headers())
    assert response.status_code == 503 and 'items' not in response.json()
    from hospital.patients import service as patients_service
    monkeypatch.setattr(patients_service, 'record_success', fail)
    response = client.get('/api/v2/patients/' + str(patient['id']), headers=headers())
    assert response.status_code == 503
