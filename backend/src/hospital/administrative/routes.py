"""Lecturas administrativas y altas V2 con clave obligatoria."""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request, Response
from sqlalchemy.orm import Session

from hospital.administrative.projections import admission_v2_projection, patient_v2_projection
from hospital.administrative.schemas import AdmissionCreateV2, PatientCreateV2, AdmissionIntakeResponse, AdmissionPageV2, PatientBasicV2, PatientDemographicsV2, PatientPageV2, ServicePage, SitePage
from hospital.administrative.service import create_patient_v2, create_admission_v2, list_catalog
from hospital.admissions.schemas import AdmissionResponse
from hospital.admissions.service import list_admissions, read_admission
from hospital.idempotency.service import request_key, apply_headers
from hospital.authorization.service import Actor
from hospital.core.database import get_session
from hospital.identity.dependencies import permitted
from hospital.patients.schemas import SearchFilters
from hospital.patients.service import read_patient, search_patients

router = APIRouter(tags=['Administración V2'])
SessionDependency = Annotated[Session, Depends(get_session)]
Limit = Annotated[int, Query(ge=1, le=100)]
Offset = Annotated[int, Query(ge=0)]


@router.get('/patients', response_model=PatientPageV2, name='patients.search')
def search(request: Request, actor: Annotated[Actor, Depends(permitted('patients.search'))],
           session: SessionDependency, filters: Annotated[SearchFilters, Query()]):
    return search_patients(session, actor=actor, request_id=UUID(request.state.request_id), filters=filters, project=patient_v2_projection)


@router.get('/patients/{patient_id}', response_model=PatientDemographicsV2 | PatientBasicV2, name='patients.read')
def read(patient_id: UUID, request: Request, actor: Annotated[Actor, Depends(permitted('patients.read'))], session: SessionDependency):
    return read_patient(session, actor=actor, request_id=UUID(request.state.request_id), patient_id=patient_id, project=patient_v2_projection)


@router.get('/admissions/{admission_id}', response_model=AdmissionIntakeResponse | AdmissionResponse, name='admissions.read')
def read_episode(admission_id: UUID, request: Request, actor: Annotated[Actor, Depends(permitted('admissions.read'))], session: SessionDependency):
    return read_admission(session, actor=actor, request_id=UUID(request.state.request_id), admission_id=admission_id, project=admission_v2_projection)


@router.get('/patients/{patient_id}/admissions', response_model=AdmissionPageV2, name='admissions.list')
def episodes(patient_id: UUID, request: Request, actor: Annotated[Actor, Depends(permitted('admissions.read', 'patients.read'))],
             session: SessionDependency, limit: Limit = 20, offset: Offset = 0):
    return list_admissions(session, actor=actor, request_id=UUID(request.state.request_id), patient_id=patient_id,
                           limit=limit, offset=offset, project=admission_v2_projection)


@router.get('/catalogs/sites', response_model=SitePage, name='catalogs.read')
def sites(request: Request, actor: Annotated[Actor, Depends(permitted('admissions.create'))],
          session: SessionDependency, limit: Limit = 20, offset: Offset = 0):
    return list_catalog(session, actor=actor, request_id=UUID(request.state.request_id), kind='sites', limit=limit, offset=offset)


@router.get('/catalogs/services', response_model=ServicePage, name='catalogs.read')
def services(site_id: UUID, request: Request, actor: Annotated[Actor, Depends(permitted('admissions.create'))],
             session: SessionDependency, limit: Limit = 20, offset: Offset = 0):
    return list_catalog(session, actor=actor, request_id=UUID(request.state.request_id), kind='services', site_id=site_id, limit=limit, offset=offset)


@router.post('/patients', status_code=201, response_model=PatientDemographicsV2 | PatientBasicV2, name='patients.create')
def create_patient(data: PatientCreateV2, request: Request, response: Response,
                   actor: Annotated[Actor, Depends(permitted('patients.create', 'patients.search'))], session: SessionDependency,
                   idempotency_header: Annotated[str, Header(alias='Idempotency-Key', description='UUID v4 por intención; obligatorio en V2')]):
    metadata = {}
    result = create_patient_v2(session, actor=actor, request_id=UUID(request.state.request_id), data=data,
                              idempotency_key=request_key(request, required=True), idempotency_metadata=metadata)
    apply_headers(response, metadata, version='v2', kind='patients', result=result)
    return result


@router.post('/admissions', status_code=201, response_model=AdmissionIntakeResponse | AdmissionResponse, name='admissions.create')
def create_admission(data: AdmissionCreateV2, request: Request, response: Response,
                     actor: Annotated[Actor, Depends(permitted('admissions.create'))], session: SessionDependency,
                   idempotency_header: Annotated[str, Header(alias='Idempotency-Key', description='UUID v4 por intención; obligatorio en V2')]):
    metadata = {}
    result = create_admission_v2(session, actor=actor, request_id=UUID(request.state.request_id), data=data,
                                idempotency_key=request_key(request, required=True), idempotency_metadata=metadata)
    apply_headers(response, metadata, version='v2', kind='admissions', result=result)
    return result
