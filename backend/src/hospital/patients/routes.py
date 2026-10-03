from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request, Response
from sqlalchemy.orm import Session

from hospital.idempotency.service import request_key, apply_headers
from hospital.authorization.service import Actor
from hospital.core.database import get_session
from hospital.identity.dependencies import permitted
from hospital.patients.schemas import PatientBasic, PatientCreate, PatientDemographics, PatientPage, SearchFilters
from hospital.patients.service import create_patient, read_patient, search_patients

router = APIRouter(tags=['Pacientes'])
SessionDependency = Annotated[Session, Depends(get_session)]


@router.get('/patients', response_model=PatientPage, name='patients.search')
def search(request: Request, actor: Annotated[Actor, Depends(permitted('patients.search'))],
           session: SessionDependency, filters: Annotated[SearchFilters, Query()]) -> dict:
    return search_patients(session, actor=actor, request_id=UUID(request.state.request_id), filters=filters)


@router.post('/patients', status_code=201, response_model=PatientDemographics | PatientBasic, name='patients.create')
def create(data: PatientCreate, request: Request, response: Response,
           actor: Annotated[Actor, Depends(permitted('patients.create', 'patients.search'))], session: SessionDependency,
           idempotency_header: Annotated[str | None, Header(alias='Idempotency-Key', description='UUID v4 por intención; opcional en V1')] = None) -> dict:
    metadata = {}
    result = create_patient(session, actor=actor, request_id=UUID(request.state.request_id), data=data,
                          idempotency_key=request_key(request), idempotency_metadata=metadata)
    apply_headers(response, metadata, version='v1', kind='patients', result=result)
    return result


@router.get('/patients/{patient_id}', response_model=PatientDemographics | PatientBasic, name='patients.read')
def read(patient_id: UUID, request: Request,
         actor: Annotated[Actor, Depends(permitted('patients.read'))], session: SessionDependency) -> dict:
    return read_patient(session, actor=actor, request_id=UUID(request.state.request_id), patient_id=patient_id)
