"""Listas explícitas de campos; no serializar entidades ORM completas."""
from collections.abc import Mapping
from typing import Any, Literal

from hospital.authorization.service import Actor, authorize

PATIENT_BASIC = ("id", "folio", "identity_status", "given_names", "family_name", "second_family_name")
PATIENT_DEMOGRAPHICS = ("birth_date", "identifiers", "created_at", "created_by")
ADMISSION_FIELDS = ("id", "folio", "patient_id", "type", "status", "created_at", "created_by")


def patient_projection(actor: Actor, data: Mapping[str, Any], *, operation: Literal["patients.search", "patients.read", "patients.create", "patients.create_verified"] = "patients.read") -> dict[str, Any]:
    authorize(actor, operation)
    fields = PATIENT_BASIC
    if "patients.read_demographics" in actor.permissions:
        fields += PATIENT_DEMOGRAPHICS
    return {field: data[field] for field in fields}


def admission_projection(actor: Actor, data: Mapping[str, Any], *, operation: Literal["admissions.read", "admissions.create", "admissions.list"] = "admissions.read") -> dict[str, Any]:
    authorize(actor, operation)
    return {field: data[field] for field in ADMISSION_FIELDS}
