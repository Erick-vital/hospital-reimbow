from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

AdmissionType = Literal['emergency', 'outpatient', 'inpatient']


class AdmissionCreate(BaseModel):
    model_config = ConfigDict(extra='forbid')
    patient_id: UUID
    type: AdmissionType


class AdmissionResponse(BaseModel):
    id: UUID
    folio: str
    patient_id: UUID
    type: AdmissionType
    status: Literal['open']
    created_at: datetime
    created_by: UUID


class AdmissionPage(BaseModel):
    items: list[AdmissionResponse]
    limit: int
    offset: int
    total: int
