from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class Output(BaseModel):
    model_config = ConfigDict(extra='forbid')


class ClinicalPatient(Output):
    id: UUID
    folio: str
    given_names: str | None
    family_name: str | None
    second_family_name: str | None
    identity_status: Literal['provisional', 'verified']
    verification_quality: Literal['pending', 'documented', 'legacy_unsubstantiated']


class CatalogItem(Output):
    id: UUID
    code: str
    name: str


class CatalogValue(Output):
    state: Literal['known', 'unknown', 'not_provided', 'not_applicable']
    value: CatalogItem | None


class DateValue(Output):
    state: Literal['known', 'unknown', 'not_provided', 'not_applicable']
    value: datetime | None


class ClinicalEpisode(Output):
    id: UUID
    folio: str
    patient_id: UUID
    type: Literal['emergency', 'outpatient', 'inpatient']
    status: Literal['open']
    created_at: datetime
    admitted_at: DateValue
    site: CatalogValue
    service: CatalogValue


class Attention(Output):
    patient: ClinicalPatient
    episode: ClinicalEpisode


class AttentionPage(Output):
    items: list[Attention]
    total: int
    limit: int
    offset: int


class EpisodeContext(Output):
    episode: ClinicalEpisode


class EpisodeContextPage(Output):
    items: list[EpisodeContext]
    total: int
    limit: int
    offset: int


class PatientContext(Output):
    patient: ClinicalPatient
    attentions: EpisodeContextPage | None = None
