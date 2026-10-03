"""Permisos explícitos compartidos por dependencias HTTP y servicios."""
from dataclasses import dataclass
from uuid import UUID

from hospital.core.errors import ApplicationError


PERMISSIONS = frozenset({
    "patients.search", "patients.read", "patients.read_demographics",
    "patients.create", "patients.verify_identity", "admissions.create",
    "admissions.read", "admissions.read_intake", "audit.read",
})

# Operaciones compuestas: un permiso de campos nunca concede acceso al recurso.
OPERATION_PERMISSIONS = {
    "patients.search": ("patients.search",),
    "patients.read": ("patients.read",),
    "patients.create": ("patients.create", "patients.search"),
    "patients.create_verified": ("patients.create", "patients.search", "patients.verify_identity"),
    "admissions.create": ("admissions.create",),
    "admissions.read": ("admissions.read",),
    "admissions.list": ("admissions.read", "patients.read"),
    "patients.replay": ("patients.create", "patients.search"),
    "admissions.replay": ("admissions.create",),
    "catalogs.read": ("admissions.create",),
    "audit.read": ("audit.read",),
}


@dataclass(frozen=True)
class Actor:
    id: UUID
    actor_key: str
    permissions: frozenset[str]


def require_permissions(actor: Actor, *permissions: str) -> None:
    if not set(permissions).issubset(actor.permissions):
        raise ApplicationError(403, "PERMISSION_DENIED", "Permiso insuficiente")


def authorize(actor: Actor, operation: str) -> None:
    # Una operación desconocida es un error del programador; nunca permite acceso.
    require_permissions(actor, *OPERATION_PERMISSIONS[operation])
