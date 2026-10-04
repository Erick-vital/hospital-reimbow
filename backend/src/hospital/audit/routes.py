from datetime import datetime
from typing import Annotated, Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from hospital.audit.service import list_events
from hospital.authorization.service import Actor
from hospital.core.database import get_session
from hospital.identity.dependencies import permitted

router = APIRouter(tags=["Auditoría"])
Action = Literal["patients.search", "patients.create", "patients.read", "admissions.create", "admissions.read", "admissions.list", "audit.read", "identity.read", "catalogs.read", "patients.replay", "admissions.replay", "clinical.attentions.read", "clinical.context.read", "clinical.catalogs.read"]


class AuditResponse(BaseModel):
    id: UUID
    actor_id: UUID | None
    action: Action
    resource_type: str | None
    resource_id: UUID | None
    result: Literal["success", "denied"]
    created_at: datetime
    request_id: UUID
    metadata: dict[str, Any]


class AuditPage(BaseModel):
    items: list[AuditResponse]
    limit: int
    offset: int
    total: int


@router.get("/audit", response_model=AuditPage, name="audit.read")
def audit(request: Request, actor: Annotated[Actor, Depends(permitted("audit.read"))],
          session: Annotated[Session, Depends(get_session)],
          limit: Annotated[int, Query(ge=1, le=100)] = 20,
          offset: Annotated[int, Query(ge=0)] = 0,
          resource_id: UUID | None = None, action: Action | None = None) -> dict:
    return list_events(session, actor=actor, request_id=UUID(request.state.request_id),
                       limit=limit, offset=offset, resource_id=resource_id, action=action)
