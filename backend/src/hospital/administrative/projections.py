from sqlalchemy import select

from hospital.administrative.models import AdmissionIntake, PatientCollectionItem, PatientProfile, Verification, VerificationEvidence
from hospital.administrative.schemas import Description, IdentityStates, Intake, Profile
from hospital.admissions.service import snapshot as admission_snapshot
from hospital.authorization.projections import admission_projection, patient_projection
from hospital.patients.service import snapshot as patient_snapshot


def patient_v2_projection(session, actor, patient, operation='patients.read'):
    result = patient_projection(actor, patient_snapshot(patient), operation=operation)
    # Calidad básica sin fuentes/valores contrastados.
    verification = session.get(Verification, patient.id)
    result['verification_quality'] = ('documented' if verification else
                                      'legacy_unsubstantiated' if patient.identity_status == 'verified' else 'pending')
    if 'patients.read_demographics' not in actor.permissions:
        return result
    profile = session.get(PatientProfile, patient.id)
    result['administrative_origin'] = 'v2' if profile else 'legacy'
    result['is_unidentified'] = profile.is_unidentified if profile else None
    # No deducir desconocido V1 únicamente por falta de nombre.
    if profile:
        data = profile.data
        administrative = {k: data[k] for k in ('registered_sex', 'nationality')}
        for kind, state in data['collection_states'].items():
            administrative[kind] = {'state': state, 'value': [] if state == 'known' else None}
        for item in session.scalars(select(PatientCollectionItem).where(PatientCollectionItem.patient_id == patient.id)
                                    .order_by(PatientCollectionItem.kind, PatientCollectionItem.position)):
            administrative[item.kind]['value'].append(item.data)
        result.update(administrative_profile=administrative, identity_field_states=data['identity_field_states'],
                      unidentified_description=data['unidentified_description'])
    else:
        states = IdentityStates().model_dump()
        for field in states:
            if getattr(patient, field) is not None:
                states[field] = 'known'
        result.update(administrative_profile=Profile().model_dump(mode='json'), identity_field_states=states,
                      unidentified_description=Description().model_dump(mode='json'))
    result['verification'] = None
    if verification:
        evidence = session.scalars(select(VerificationEvidence).where(VerificationEvidence.patient_id == patient.id)
                                   .order_by(VerificationEvidence.field))
        result['verification'] = {'verified_by': verification.verified_by, 'verified_at': verification.verified_at,
            'evidence': [{'field': e.field, 'source_kind': e.source_kind, 'source_reference': e.source_reference,
                          'snapshot': e.snapshot} for e in evidence]}
    return result


def admission_v2_projection(session, actor, admission, operation='admissions.read'):
    result = admission_projection(actor, admission_snapshot(admission), operation=operation)
    if 'admissions.read_intake' in actor.permissions:
        intake = session.get(AdmissionIntake, admission.id)
        result['intake'] = intake.data if intake else Intake().model_dump(mode='json')
        result['intake_origin'] = 'v2' if intake else 'legacy'
    return result
