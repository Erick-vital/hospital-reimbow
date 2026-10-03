from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from hospital.core.database import get_session

router = APIRouter(prefix="/health", tags=["Salud"])


class LiveResponse(BaseModel):
    status: Literal["alive"] = "alive"


class ReadyResponse(BaseModel):
    status: Literal["ready"] = "ready"


@router.get("/live", response_model=LiveResponse)
def live() -> LiveResponse:
    return LiveResponse()


@router.get("/ready", response_model=ReadyResponse, responses={503: {"description": "Base no disponible"}})
def ready(session: Annotated[Session, Depends(get_session)]) -> ReadyResponse:
    session.execute(text("SELECT 1"))
    return ReadyResponse()
