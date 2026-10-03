import hashlib
import json
from datetime import timedelta
from uuid import UUID

from fastapi import Request, Response
from sqlalchemy import func, select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import DBAPIError

from hospital.audit.service import record_success
from hospital.core.errors import ApplicationError
from hospital.idempotency.models import IdempotencyRecord


def request_key(request: Request, *, required=False) -> UUID | None:
    values = request.headers.getlist('Idempotency-Key')
    if not values and not required:
        return None
    try:
        if len(values) != 1 or len(values[0]) != 36:
            raise ValueError
        key = UUID(values[0])
        if key.version != 4 or str(key) != values[0].lower():
            raise ValueError
        return key
    except ValueError:
        raise ApplicationError(422, 'VALIDATION_ERROR', 'Idempotency-Key requiere un UUID v4 canónico único') from None


def fingerprint(operation, data):
    body = data.model_dump(mode='json', exclude={'search_id'})
    if 'identifiers' in body:
        body['identifiers'] = sorted(body['identifiers'], key=lambda i: (i['system'], i['value']))
    encoded = json.dumps(body, sort_keys=True, ensure_ascii=False, separators=(',', ':'))
    return hashlib.sha256((operation + '\n1\n' + encoded).encode('utf-8')).hexdigest()


def reserve(session, actor, operation, key, data):
    digest = fingerprint(operation, data)
    previous = session.execute(text("SELECT current_setting('lock_timeout'), current_setting('statement_timeout')")).one()
    # El timeout general de la conexión (2 s) no debe anticipar los 5 s pactados.
    session.execute(text("SELECT set_config('lock_timeout','5s',true), set_config('statement_timeout','0',true)"))
    try:
        row_id = session.scalar(insert(IdempotencyRecord).values(actor_id=actor.id, operation=operation, key=key, fingerprint=digest)
            .on_conflict_do_nothing(constraint='uq_idempotency_actor_operation_key').returning(IdempotencyRecord.id))
    except DBAPIError as exc:
        if getattr(exc.orig, 'sqlstate', None) == '55P03':
            # El contexto transaccional del servicio revierte la reserva fallida.
            raise ApplicationError(409, 'IDEMPOTENCY_IN_PROGRESS', 'Alta en curso; reintente el mismo registro') from None
        raise
    session.execute(text("SELECT set_config('lock_timeout',:lock,true), set_config('statement_timeout',:statement,true)"),
                    {'lock': previous[0], 'statement': previous[1]})
    if row_id is not None:
        return session.get(IdempotencyRecord, row_id), False
    record = session.scalar(select(IdempotencyRecord).where(IdempotencyRecord.actor_id == actor.id,
        IdempotencyRecord.operation == operation, IdempotencyRecord.key == key))
    if session.scalar(select(func.clock_timestamp())) >= record.expires_at:
        raise ApplicationError(409, 'IDEMPOTENCY_EXPIRED', 'Garantía vencida; consulte el registro antes de otra alta')
    if record.fingerprint != digest:
        raise ApplicationError(409, 'IDEMPOTENCY_CONFLICT', 'Clave utilizada con datos diferentes')
    return record, True


def execute_create(session, *, actor, request_id, data, operation, key, metadata, create, project, model):
    """El llamador autoriza antes; recurso, reserva y auditoría comparten commit."""
    with session.begin():
        record, replayed = reserve(session, actor, operation, key, data) if key else (None, False)
        kind = operation.split('.')[1]
        if replayed:
            resource = session.get(model, record.patient_id if kind == 'patients' else record.admission_id)
            result = project(resource)
            record_success(session, actor=actor, request_id=request_id, action=kind + '.replay', resource_id=resource.id)
        else:
            resource = create()
            result = project(resource)
            if record is not None:
                record.state = 'completed'
                if kind == 'patients':
                    record.patient_id = resource.id
                else:
                    record.admission_id = resource.id
                record.created_at = session.scalar(select(func.clock_timestamp()))
                record.expires_at = record.created_at + timedelta(hours=24)
                session.flush()
        response_metadata = {'replayed': replayed, 'expires_at': record.expires_at} if record else {}
    # No anunciar éxito ni cabeceras hasta que el commit haya terminado.
    if metadata is not None:
        metadata.update(response_metadata)
    return result


def apply_headers(response: Response, metadata, *, version, kind, result):
    response.headers['Location'] = f"/api/{version}/{kind}/{result['id']}"
    if metadata:
        response.status_code = 200 if metadata['replayed'] else 201
        response.headers['Idempotency-Replayed'] = str(metadata['replayed']).lower()
        response.headers['Idempotency-Expires-At'] = metadata['expires_at'].isoformat().replace('+00:00', 'Z')
