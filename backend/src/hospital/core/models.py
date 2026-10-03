"""Registro explícito de modelos para Alembic; no crea tablas al arrancar."""
from hospital.identity.models import User
from hospital.authorization.models import Permission, Role, RolePermission, UserRole
from hospital.audit.models import AuditEvent
from hospital.patients.models import Patient, PatientIdentifier, PatientSearch

from hospital.admissions.models import Admission

__all__ = ["User", "Permission", "Role", "RolePermission", "UserRole", "AuditEvent", "Patient", "PatientIdentifier", "PatientSearch", "Admission"]
