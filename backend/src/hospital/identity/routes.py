from uuid import UUID
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from hospital.audit.service import record_success
from hospital.core.database import get_session

from hospital.identity.dependencies import CurrentActor

router = APIRouter(prefix="/identity", tags=["Identidad local"])


class IdentityResponse(BaseModel):
    id: UUID
    actor_key: str
    permissions: list[str]


@router.get("/me", response_model=IdentityResponse, name="identity.read")
def me(request: Request, actor: CurrentActor, session: Annotated[Session, Depends(get_session)]) -> IdentityResponse:
    with session.begin():
        record_success(session, actor=actor, action="identity.read", request_id=UUID(request.state.request_id))
    return IdentityResponse(id=actor.id, actor_key=actor.actor_key, permissions=sorted(actor.permissions))
