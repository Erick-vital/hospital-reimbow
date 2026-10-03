import logging
from collections.abc import Mapping
from typing import Any
from uuid import UUID

from fastapi.encoders import jsonable_encoder
from sqlalchemy import func, select, true
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, aliased

from hospital.audit.models import ACTIONS, AuditEvent
from hospital.authorization.projections import ADMISSION_FIELDS, PATIENT_BASIC, PATIENT_DEMOGRAPHICS
from hospital.authorization.service import Actor, authorize

logger = logging.getLogger("hospital.audit")


def record_success(session: Session, *, actor: Actor, action: str, request_id: UUID,
                   resource_id: UUID | None = None, new_values: Mapping[str, Any] | None = None) -> AuditEvent:
    """Añade/flush en la transacción del servicio; nunca inicia ni confirma otra."""
    if not session.in_transaction():
        raise RuntimeError("Auditoría de éxito requiere transacción del servicio")
    if action not in ACTIONS:
        raise ValueError("Acción de auditoría desconocida")
    if action != "identity.read":
        authorize(actor, action)
    metadata = {}
    if action in {"patients.create", "admissions.create"}:
        if resource_id is None or new_values is None:
            raise ValueError("Auditoría de creación requiere recurso y valores nuevos")
        fields = PATIENT_BASIC + PATIENT_DEMOGRAPHICS if action == "patients.create" else ADMISSION_FIELDS
        values = {field: new_values[field] for field in fields}
        if action == "patients.create":
            values["identifiers"] = [{"system": i["system"], "value": i["value"]} for i in values["identifiers"]]
            if values["identity_status"] == "verified":
                authorize(actor, "patients.create_verified")
        metadata = {"old": None, "new": jsonable_encoder(values)}
    elif new_values is not None:
        raise ValueError("Lecturas/búsquedas no almacenan datos personales")
    event = AuditEvent(actor_id=actor.id, action=action, resource_type=action.split(".")[0],
                       resource_id=resource_id, result="success", request_id=request_id, event_metadata=metadata)
    session.add(event)
    session.flush()  # Falla aquí o al commit: el servicio debe revertir la unidad completa.
    return event


def record_denial(sessions, *, actor_id: UUID | None, action: str, request_id: UUID, code: str) -> None:
    """Canal separado de la unidad revertida; sólo datos mínimos y fallback técnico."""
    if action not in ACTIONS or code not in {"IDENTITY_REQUIRED", "PERMISSION_DENIED"}:
        raise ValueError("Denegación de auditoría inválida")
    try:
        with sessions.begin() as session:
            session.add(AuditEvent(actor_id=actor_id, action=action, resource_type=action.split(".")[0],
                                   resource_id=None, result="denied", request_id=request_id,
                                   event_metadata={"code": code}))
    except SQLAlchemyError:
        # No SQL, excepción completa, actor, parámetros, cuerpos ni cabeceras.
        logger.error("AUDIT_DENIAL_UNAVAILABLE code=%s request_id=%s", code, request_id)


def list_events(session: Session, *, actor: Actor, request_id: UUID, limit: int = 20,
                offset: int = 0, resource_id: UUID | None = None, action: str | None = None) -> dict:
    authorize(actor, "audit.read")
    with session.begin():
        filters = []
        if resource_id is not None:
            filters.append(AuditEvent.resource_id == resource_id)
        if action is not None:
            filters.append(AuditEvent.action == action)
        # Una sola sentencia: total y página comparten snapshot incluso con escrituras.
        count = select(func.count()).select_from(AuditEvent).where(*filters).subquery()
        page = select(AuditEvent).where(*filters).order_by(AuditEvent.created_at, AuditEvent.id).limit(limit).offset(offset).subquery()
        event_alias = aliased(AuditEvent, page)
        rows = session.execute(
            select(count.c[0], event_alias).select_from(count).outerjoin(page, true())
            .order_by(event_alias.created_at, event_alias.id)
        ).all()
        total = rows[0][0]
        items = [{"id": e.id, "actor_id": e.actor_id, "action": e.action, "resource_type": e.resource_type,
                  "resource_id": e.resource_id, "result": e.result, "created_at": e.created_at,
                  "request_id": e.request_id, "metadata": e.event_metadata} for _, e in rows if e is not None]
        record_success(session, actor=actor, action="audit.read", request_id=request_id)
    return {"items": items, "limit": limit, "offset": offset, "total": total}
