from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy import select

from hospital.authorization.models import Permission, RolePermission, UserRole
from hospital.authorization.service import Actor, require_permissions
from hospital.core.errors import ApplicationError
from hospital.identity.models import User


def get_actor(request: Request) -> Actor:
    settings = request.app.state.settings
    values = request.headers.getlist("X-Dev-Actor")
    if (settings.app_env not in {"development", "test"}
            or not settings.dev_identity_enabled or len(values) != 1
            or not values[0] or len(values[0]) > 100):
        raise ApplicationError(401, "IDENTITY_REQUIRED", "Identidad requerida")
    # Sesión breve independiente: no deja autobegin en la unidad de trabajo del
    # servicio. Cada solicitud consulta estado/permisos actuales, sin caché global.
    with request.app.state.database.sessions() as session:
        user = session.scalar(select(User).where(
            User.actor_key == values[0], User.provider == "development", User.status == "active",
        ))
        if user is None:
            raise ApplicationError(401, "IDENTITY_REQUIRED", "Identidad requerida")
        codes = session.scalars(select(Permission.code).join(
            RolePermission, RolePermission.permission_id == Permission.id,
        ).join(UserRole, UserRole.role_id == RolePermission.role_id).where(
            UserRole.user_id == user.id,
        ))
        actor = Actor(user.id, user.actor_key, frozenset(codes))
        request.state.actor = actor
        return actor


CurrentActor = Annotated[Actor, Depends(get_actor)]


def permitted(*permissions: str):
    """Dependencia de ruta; los servicios también deben verificar sus permisos."""
    def dependency(actor: CurrentActor) -> Actor:
        require_permissions(actor, *permissions)
        return actor
    return dependency
