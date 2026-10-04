from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from hospital.administrative.schemas import ServicePage, SitePage
from hospital.authorization.service import Actor, OPERATION_PERMISSIONS
from hospital.clinical.schemas import Attention, AttentionPage, PatientContext
from hospital.clinical.service import list_attentions, list_catalog, read_context
from hospital.core.database import get_session
from hospital.identity.dependencies import permitted

router = APIRouter(tags=['Contexto clínico V3'])
SessionDependency = Annotated[Session, Depends(get_session)]
ContextActor = Annotated[Actor, Depends(permitted(*OPERATION_PERMISSIONS['clinical.context.read']))]
AttentionActor = Annotated[Actor, Depends(permitted(*OPERATION_PERMISSIONS['clinical.attentions.read']))]
CatalogActor = Annotated[Actor, Depends(permitted(*OPERATION_PERMISSIONS['clinical.catalogs.read']))]
Limit = Annotated[int, Query(ge=1, le=100)]
Offset = Annotated[int, Query(ge=0)]


@router.get('/attentions', response_model=AttentionPage, name='clinical.attentions.read')
def attentions(request: Request, actor: AttentionActor, session: SessionDependency,
               type: Literal['emergency', 'outpatient', 'inpatient'] | None = None,
               site_id: UUID | None = None, service_id: UUID | None = None, limit: Limit = 20, offset: Offset = 0):
    return list_attentions(session, actor=actor, request_id=UUID(request.state.request_id),
        type=type, site_id=site_id, service_id=service_id, limit=limit, offset=offset)


@router.get('/patients/{patient_id}/attentions', response_model=AttentionPage, name='clinical.attentions.read')
def patient_attentions(patient_id: UUID, request: Request, actor: AttentionActor, session: SessionDependency, limit: Limit = 20, offset: Offset = 0):
    return list_attentions(session, actor=actor, request_id=UUID(request.state.request_id), patient_id=patient_id, limit=limit, offset=offset)


@router.get('/attentions/{episode_id}/context', response_model=Attention, name='clinical.context.read')
def episode_context(episode_id: UUID, request: Request, actor: ContextActor, session: SessionDependency):
    return read_context(session, actor=actor, request_id=UUID(request.state.request_id), episode_id=episode_id)


@router.get('/patients/{patient_id}/context', response_model=PatientContext, response_model_exclude_unset=True, name='clinical.context.read')
def patient_context(patient_id: UUID, request: Request, actor: ContextActor, session: SessionDependency, limit: Limit = 20, offset: Offset = 0):
    return read_context(session, actor=actor, request_id=UUID(request.state.request_id), patient_id=patient_id, limit=limit, offset=offset)


@router.get('/catalogs/sites', response_model=SitePage, name='clinical.catalogs.read')
def sites(request: Request, actor: CatalogActor, session: SessionDependency, limit: Limit = 20, offset: Offset = 0):
    return list_catalog(session, actor=actor, request_id=UUID(request.state.request_id), kind='sites', limit=limit, offset=offset)


@router.get('/catalogs/services', response_model=ServicePage, name='clinical.catalogs.read')
def services(site_id: UUID, request: Request, actor: CatalogActor, session: SessionDependency, limit: Limit = 20, offset: Offset = 0):
    return list_catalog(session, actor=actor, request_id=UUID(request.state.request_id), kind='services', site_id=site_id, limit=limit, offset=offset)
