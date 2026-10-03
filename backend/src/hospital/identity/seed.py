"""Semilla explícita de desarrollo, atómica e idempotente sobre PostgreSQL."""
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from hospital.authorization.models import Permission, Role, RolePermission, UserRole
from hospital.authorization.service import PERMISSIONS
from hospital.core.config import Settings
from hospital.identity.models import User
from hospital.administrative.seed import seed_catalogs

ROLE_PERMISSIONS = {
    "admision-demo": PERMISSIONS - {"patients.verify_identity", "audit.read"},
    "supervisor-demo": PERMISSIONS,
    "consulta-demo": frozenset({"patients.search", "patients.read", "admissions.read"}),
}
ACTOR_ROLES = {
    "admision-demo": "admision-demo",
    "supervisor-demo": "supervisor-demo",
    "consulta-demo": "consulta-demo",
    "inactivo-demo": "consulta-demo",
}


class SeedError(RuntimeError):
    """Mensaje público sin datos de conexión."""


def seed_local_identity(session: Session, settings: Settings) -> dict[str, int]:
    if settings.app_env not in {"development", "test"}:
        raise SeedError("Semilla ficticia prohibida fuera de desarrollo/pruebas")
    # La bandera controla HTTP, no la preparación explícita de datos locales.
    # begin exige una sesión limpia y revierte toda la semilla ante discrepancias.
    with session.begin():
        seed_catalogs(session)
        for code in sorted(PERMISSIONS):
            session.execute(insert(Permission).values(code=code).on_conflict_do_nothing(index_elements=["code"]))
        permissions = {p.code: p.id for p in session.scalars(select(Permission).where(Permission.code.in_(PERMISSIONS)))}
        roles = {}
        for code, expected in ROLE_PERMISSIONS.items():
            session.execute(insert(Role).values(code=code).on_conflict_do_nothing(index_elements=["code"]))
            role = session.scalar(select(Role).where(Role.code == code))
            roles[code] = role.id
            current = set(session.scalars(select(Permission.code).join(RolePermission).where(RolePermission.role_id == role.id)))
            if current - expected:
                raise SeedError("Rol ficticio con permisos ajenos a la semilla; revisar configuración")
            for permission in sorted(expected):
                session.execute(insert(RolePermission).values(role_id=role.id, permission_id=permissions[permission]).on_conflict_do_nothing())
        for key, role_code in ACTOR_ROLES.items():
            status = "inactive" if key == "inactivo-demo" else "active"
            session.execute(insert(User).values(actor_key=key, provider="development", subject=key, status=status).on_conflict_do_nothing())
            user = session.scalar(select(User).where(User.actor_key == key))
            if (user is None or user.provider != "development" or user.subject != key
                    or (key == "inactivo-demo" and user.status != "inactive")):
                raise SeedError("Identidad ficticia incompatible; revisar configuración")
            current_roles = set(session.scalars(select(UserRole.role_id).where(UserRole.user_id == user.id)))
            if current_roles - {roles[role_code]}:
                raise SeedError("Actor ficticio con roles ajenos a la semilla; revisar configuración")
            # No reactivar usuarios previamente suspendidos ni tocar identidades ajenas.
            session.execute(insert(UserRole).values(user_id=user.id, role_id=roles[role_code]).on_conflict_do_nothing())
    return {"actors": len(ACTOR_ROLES), "roles": len(ROLE_PERMISSIONS), "permissions": len(PERMISSIONS)}
