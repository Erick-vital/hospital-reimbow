from datetime import date, datetime, timezone
from typing import Annotated, Generic, Literal, TypeVar
from uuid import UUID

from pydantic import BaseModel, Field, StrictInt, field_validator, model_validator

from hospital.admissions.schemas import AdmissionCreate
from hospital.patients.schemas import InputModel, PatientCreate, normalize_text
from hospital.patients.schemas import PatientBasic, Identifier
from hospital.admissions.schemas import AdmissionResponse

T = TypeVar('T')
State = Literal['known', 'unknown', 'not_provided', 'not_applicable']


class Absent(InputModel, Generic[T]):
    state: State = 'not_provided'
    value: T | None = None

    @model_validator(mode='after')
    def coherent(self):
        if (self.state == 'known') != (self.value is not None):
            raise ValueError('Estado y valor incompatibles')
        return self


class TextInput(InputModel):
    @field_validator('*', mode='before')
    @classmethod
    def normalize(cls, value):
        return normalize_text(value) if isinstance(value, str) else value


Short = Annotated[str, Field(min_length=1, max_length=100)]
Text200 = Annotated[str, Field(min_length=1, max_length=200)]
PhoneNumber = Annotated[str, Field(min_length=1, max_length=40)]


class TextAbsent(Absent[T]):
    @field_validator('value', mode='before')
    @classmethod
    def normalize(cls, value):
        return normalize_text(value) if isinstance(value, str) else value


class Phone(TextInput):
    kind: Literal['personal', 'fixed', 'work', 'other']
    number: PhoneNumber


class Address(TextInput):
    kind: Literal['principal', 'temporary', 'fiscal', 'correspondence', 'other']
    street: Text200 | None = None
    exterior: Text200 | None = None
    interior: Text200 | None = None
    neighborhood: Text200 | None = None
    postal_code: Annotated[str, Field(min_length=1, max_length=20)] | None = None
    municipality: Text200 | None = None
    state: Text200 | None = None
    country: Text200 | None = None
    references: Annotated[str, Field(min_length=1, max_length=500)] | None = None

    @model_validator(mode='after')
    def component(self):
        if not any(v is not None for k, v in self.model_dump().items() if k != 'kind'):
            raise ValueError('Domicilio vacío')
        return self


class Contact(TextInput):
    name: Text200
    relationship: TextAbsent[Short] = Field(default_factory=TextAbsent[Short])
    phone: TextAbsent[PhoneNumber] = Field(default_factory=TextAbsent[PhoneNumber])


class Profile(InputModel):
    registered_sex: TextAbsent[Short] = Field(default_factory=TextAbsent[Short])
    nationality: TextAbsent[Short] = Field(default_factory=TextAbsent[Short])
    phones: Absent[Annotated[list[Phone], Field(max_length=10)]] = Field(default_factory=Absent)
    addresses: Absent[Annotated[list[Address], Field(max_length=10)]] = Field(default_factory=Absent)
    emergency_contacts: Absent[Annotated[list[Contact], Field(max_length=10)]] = Field(default_factory=Absent)


class EstimatedAge(InputModel):
    min_years: Annotated[StrictInt, Field(ge=0, le=150)]
    max_years: Annotated[StrictInt, Field(ge=0, le=150)]

    @model_validator(mode='after')
    def range(self):
        if self.min_years > self.max_years:
            raise ValueError('Rango estimado incoherente')
        return self


class Description(InputModel):
    apparent_sex: TextAbsent[Short] = Field(default_factory=TextAbsent[Short])
    estimated_age: Absent[EstimatedAge] = Field(default_factory=Absent[EstimatedAge])
    identifying_features: TextAbsent[Annotated[str, Field(min_length=1, max_length=1000)]] = Field(default_factory=TextAbsent)
    origin: TextAbsent[Text200] = Field(default_factory=TextAbsent[Text200])
    transferred_by: TextAbsent[Text200] = Field(default_factory=TextAbsent[Text200])


class IdentityStates(InputModel):
    given_names: State = 'not_provided'
    family_name: State = 'not_provided'
    second_family_name: State = 'not_provided'
    birth_date: State = 'not_provided'


class Evidence(TextInput):
    field: Literal['full_name', 'birth_date', 'CURP']
    source_kind: Literal['official_document', 'institutional_document']
    source_reference: Text200


class PatientCreateV2(PatientCreate):
    is_unidentified: bool = False
    administrative_profile: Profile = Field(default_factory=Profile)
    unidentified_description: Description = Field(default_factory=Description)
    identity_field_states: IdentityStates = Field(default_factory=IdentityStates)
    verification: Annotated[list[Evidence], Field(max_length=3)] = Field(default_factory=list)

    @model_validator(mode='after')
    def expanded_consistency(self):
        for field in type(self.identity_field_states).model_fields:
            present = getattr(self, field) is not None
            if field not in self.identity_field_states.model_fields_set:
                setattr(self.identity_field_states, field, 'known' if present else 'not_provided')
            if (getattr(self.identity_field_states, field) == 'known') != present:
                raise ValueError('Estado de identidad incompatible')
        if self.is_unidentified and (self.identity_status != 'provisional' or self.identifiers
                or any(getattr(self, f) is not None for f in type(self.identity_field_states).model_fields)):
            raise ValueError('Desconocido con identidad informada')
        if not self.is_unidentified and any(v.state != 'not_provided' for v in self.unidentified_description.__dict__.values()):
            raise ValueError('Descripción requiere desconocido explícito')
        fields = [e.field for e in self.verification]
        if len(set(fields)) != len(fields):
            raise ValueError('Evidencia duplicada')
        if self.identity_status == 'verified':
            if 'full_name' not in fields or not ({'birth_date', 'CURP'} & set(fields)):
                raise ValueError('Verificación requiere dos identificadores contrastados')
        elif fields:
            raise ValueError('Evidencia incompatible con estado provisional')
        if ('full_name' in fields and not self.given_names) or ('birth_date' in fields and self.birth_date is None) or (
                'CURP' in fields and not any(i.system == 'CURP' for i in self.identifiers)):
            raise ValueError('Evidencia de campo ausente')
        # CURP es un identificador único de verificación; no aceptar dos valores ambiguos.
        if 'CURP' in fields and sum(i.system == 'CURP' for i in self.identifiers) != 1:
            raise ValueError('CURP de verificación ambiguo')
        return self


class DateAbsent(Absent[datetime]):
    @field_validator('value', mode='before')
    @classmethod
    def explicit_date(cls, value):
        if value is None or isinstance(value, datetime):
            return value
        if not isinstance(value, str):
            raise ValueError('Ingreso requiere fecha ISO con zona')
        return datetime.fromisoformat(value)


class Intake(InputModel):
    admitted_at: DateAbsent = Field(default_factory=DateAbsent)
    site_id: Absent[UUID] = Field(default_factory=Absent[UUID])
    service_id: Absent[UUID] = Field(default_factory=Absent[UUID])
    origin: TextAbsent[Text200] = Field(default_factory=TextAbsent[Text200])
    reason_for_visit: TextAbsent[Annotated[str, Field(min_length=1, max_length=1000)]] = Field(default_factory=TextAbsent)

    @model_validator(mode='after')
    def clinical_time(self):
        value = self.admitted_at.value
        if value is not None:
            if value.tzinfo is None or value.utcoffset() is None:
                raise ValueError('Ingreso requiere zona horaria')
            value = value.astimezone(timezone.utc)
            if value > datetime.now(timezone.utc):
                raise ValueError('Ingreso futuro')
            self.admitted_at.value = value
        if self.service_id.state == 'known' and self.site_id.state != 'known':
            raise ValueError('Servicio requiere sede')
        return self


class AdmissionCreateV2(AdmissionCreate):
    intake: Intake = Field(default_factory=Intake)

    @model_validator(mode='after')
    def required_intake(self):
        if self.type != 'emergency' and any(getattr(self.intake, f).state != 'known' for f in ('admitted_at', 'site_id', 'service_id')):
            raise ValueError('Fecha, sede y servicio requeridos')
        return self


class EvidenceResponse(Evidence):
    snapshot: dict


class VerificationResponse(BaseModel):
    verified_by: UUID
    verified_at: datetime
    evidence: list[EvidenceResponse]


class PatientBasicV2(PatientBasic):
    verification_quality: Literal['documented', 'pending', 'legacy_unsubstantiated']


class PatientDemographicsV2(PatientBasicV2):
    birth_date: date | None
    identifiers: list[Identifier]
    created_at: datetime
    created_by: UUID
    administrative_origin: Literal['v2', 'legacy']
    is_unidentified: bool | None
    administrative_profile: Profile
    unidentified_description: Description
    identity_field_states: IdentityStates
    verification: VerificationResponse | None


class PatientPageV2(BaseModel):
    items: list[PatientDemographicsV2 | PatientBasicV2]
    limit: int
    offset: int
    total: int
    search_id: UUID


class AdmissionIntakeResponse(AdmissionResponse):
    intake: Intake
    intake_origin: Literal['v2', 'legacy']


class AdmissionPageV2(BaseModel):
    items: list[AdmissionIntakeResponse | AdmissionResponse]
    limit: int
    offset: int
    total: int


class SiteResponse(BaseModel):
    id: UUID
    code: str
    name: str


class ServiceResponse(SiteResponse):
    site_id: UUID


class SitePage(BaseModel):
    items: list[SiteResponse]
    limit: int
    offset: int
    total: int


class ServicePage(SitePage):
    items: list[ServiceResponse]
