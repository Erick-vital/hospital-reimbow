from datetime import date, datetime, timezone
import re
from typing import Literal
import unicodedata
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def normalize_text(value: str) -> str:
    return unicodedata.normalize('NFC', value.strip())


def full_name(data) -> str:
    return ' '.join(v for v in (data.given_names, data.family_name, data.second_family_name) if v)


class InputModel(BaseModel):
    model_config = ConfigDict(extra='forbid')


class Identifier(InputModel):
    system: Literal['CURP', 'TEST']
    value: str

    @field_validator('system', 'value', mode='before')
    @classmethod
    def normalize(cls, value):
        if isinstance(value, str):
            # Comprobar ASCII antes de upper: ß nunca debe transformarse en SS.
            value = value.strip()
            if not value.isascii():
                raise ValueError('Identificador debe ser ASCII')
            return value.upper()
        return value

    @model_validator(mode='after')
    def format(self):
        pattern = r'[A-Z0-9]{18}' if self.system == 'CURP' else r'[A-Z0-9_-]{1,64}'
        if not re.fullmatch(pattern, self.value):
            raise ValueError('Formato de identificador inválido')
        return self


class PatientCreate(InputModel):
    search_id: UUID | None = None
    identity_status: Literal['provisional', 'verified']
    given_names: str | None = Field(default=None, min_length=1, max_length=100)
    family_name: str | None = Field(default=None, min_length=1, max_length=100)
    second_family_name: str | None = Field(default=None, min_length=1, max_length=100)
    birth_date: date | None = None
    identifiers: list[Identifier] = Field(default_factory=list, max_length=10)

    @field_validator('given_names', 'family_name', 'second_family_name', mode='before')
    @classmethod
    def names(cls, value):
        return normalize_text(value) if isinstance(value, str) else value

    @field_validator('birth_date')
    @classmethod
    def past_birth(cls, value):
        if value and value > datetime.now(timezone.utc).date():
            raise ValueError('Fecha futura')
        return value

    @model_validator(mode='after')
    def consistency(self):
        if self.identity_status == 'verified' and not self.given_names:
            raise ValueError('Identidad verificada requiere nombre')
        pairs = [(i.system, i.value) for i in self.identifiers]
        if len(pairs) != len(set(pairs)):
            raise ValueError('Identificadores repetidos')
        return self


class SearchFilters(InputModel):
    folio: str | None = Field(default=None, min_length=1, max_length=32)
    name: str | None = Field(default=None, min_length=1, max_length=302)
    identifier_system: str | None = None
    identifier_value: str | None = None
    unidentified: bool = False
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)

    @field_validator('name', 'folio', mode='before')
    @classmethod
    def text(cls, value):
        return normalize_text(value) if isinstance(value, str) else value

    @model_validator(mode='after')
    def filters(self):
        if (self.identifier_system is None) != (self.identifier_value is None):
            raise ValueError('Identificador requiere system y value')
        if self.identifier_system is not None:
            pair = Identifier(system=self.identifier_system, value=self.identifier_value)
            self.identifier_system, self.identifier_value = pair.system, pair.value
        present = any(v is not None for v in (self.folio, self.name, self.identifier_system))
        if self.unidentified == present:
            raise ValueError('Filtros requeridos o incompatibles')
        return self

    def evidence(self):
        return self.model_dump(exclude={'limit', 'offset'}, exclude_none=True)


class PatientBasic(BaseModel):
    id: UUID
    folio: str
    identity_status: Literal['provisional', 'verified']
    given_names: str | None
    family_name: str | None
    second_family_name: str | None


class PatientDemographics(PatientBasic):
    birth_date: date | None
    identifiers: list[Identifier]
    created_at: datetime
    created_by: UUID


class PatientPage(BaseModel):
    items: list[PatientDemographics | PatientBasic]
    limit: int
    offset: int
    total: int
    search_id: UUID
