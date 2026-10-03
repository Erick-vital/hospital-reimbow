from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy.orm import Session

from hospital.admissions.schemas import AdmissionCreate, AdmissionPage, AdmissionResponse
from hospital.admissions.service import create_admission, list_admissions, read_admission
from hospital.authorization.service import Actor
from hospital.core.database import get_session
from hospital.identity.dependencies import permitted

router = APIRouter(tags=['Episodios'])
SessionDependency = Annotated[Session, Depends(get_session)]


@router.post('/admissions', status_code=201, response_model=AdmissionResponse, name='admissions.create')
def create(data: AdmissionCreate, request: Request, response: Response,
           actor: Annotated[Actor, Depends(permitted('admissions.create'))], session: SessionDependency) -> dict:
    result = create_admission(session, actor=actor, request_id=UUID(request.state.request_id), data=data)
    response.headers['Location'] = f"/api/v1/admissions/{result['id']}"
    return result


@router.get('/admissions/{admission_id}', response_model=AdmissionResponse, name='admissions.read')
def read(admission_id: UUID, request: Request,
         actor: Annotated[Actor, Depends(permitted('admissions.read'))], session: SessionDependency) -> dict:
    return read_admission(session, actor=actor, request_id=UUID(request.state.request_id), admission_id=admission_id)


@router.get('/patients/{patient_id}/admissions', response_model=AdmissionPage, name='admissions.list')
def list_for_patient(patient_id: UUID, request: Request,
                     actor: Annotated[Actor, Depends(permitted('admissions.read', 'patients.read'))],
                     session: SessionDependency,
                     limit: Annotated[int, Query(ge=1, le=100)] = 20,
                     offset: Annotated[int, Query(ge=0)] = 0) -> dict:
    return list_admissions(session, actor=actor, request_id=UUID(request.state.request_id),
                           patient_id=patient_id, limit=limit, offset=offset)
