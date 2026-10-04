"""Proyección dedicada: nunca serializar demografía, perfil o intake completos."""
from hospital.authorization.service import authorize


def patient_projection(actor, patient, verification):
    authorize(actor, 'clinical.context.read')
    result = {key: getattr(patient, key) for key in (
        'id', 'folio', 'given_names', 'family_name', 'second_family_name', 'identity_status')}
    result['verification_quality'] = ('documented' if verification else
        'legacy_unsubstantiated' if patient.identity_status == 'verified' else 'pending')
    return result


def episode_projection(actor, episode, intake, site, service):
    authorize(actor, 'clinical.context.read')
    result = {key: getattr(episode, key) for key in ('id', 'folio', 'patient_id', 'type', 'status', 'created_at')}
    result['admitted_at'] = intake.data['admitted_at'] if intake else {'state': 'not_provided', 'value': None}
    for key, field, row in [('site', 'site_id', site), ('service', 'service_id', service)]:
        result[key] = {'state': intake.data[field]['state'] if intake else 'not_provided',
                       'value': {k: getattr(row, k) for k in ('id', 'code', 'name')} if row else None}
    return result
