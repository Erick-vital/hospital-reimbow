from contextlib import contextmanager
from uuid import uuid4

from fastapi import Depends
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import delete, select, text, update
from sqlalchemy.orm import Session, sessionmaker

from hospital.authorization.models import Permission, Role, RolePermission, UserRole
from hospital.authorization.projections import PATIENT_BASIC, PATIENT_DEMOGRAPHICS, patient_projection
from hospital.authorization.service import OPERATION_PERMISSIONS
from hospital.core.config import Settings
from hospital.core.database import Database
from hospital.identity.dependencies import permitted
from hospital.identity.models import User
from hospital.identity.seed import ACTOR_ROLES, ROLE_PERMISSIONS, SeedError, seed_local_identity
from hospital.main import create_app

pytestmark = pytest.mark.integration


@pytest.fixture
def sessions():
    settings = Settings(app_env="test", dev_identity_enabled=True)
    db = Database(settings)
    try:
        with db.engine.connect() as connection:
            assert connection.scalar(text("SELECT current_database()")) == "hospital_test"
            connection.rollback()
            outer = connection.begin()
            factory = sessionmaker(bind=connection, join_transaction_mode="create_savepoint", expire_on_commit=False)
            try:
                with factory() as session:
                    seed_local_identity(session, settings)
                yield factory
            finally:
                outer.rollback()
    finally:
        db.dispose()


@contextmanager
def api(sessions):
    app = create_app(Settings(app_env="test", dev_identity_enabled=True))
    for operation, permissions in OPERATION_PERMISSIONS.items():
        # Rutas sólo del test: no publica clínica ficticia en la aplicación real.
        def probe(actor=Depends(permitted(*permissions))):
            return {"authorized": True}
        app.add_api_route("/probe/" + operation, probe, methods=["GET"])

    @app.get("/projection")
    def projection(actor=Depends(permitted("patients.read"))):
        data = dict.fromkeys(PATIENT_BASIC + PATIENT_DEMOGRAPHICS + ("extra_secret",), "ficticio")
        return patient_projection(actor, data)

    with TestClient(app) as client:
        app.state.database.sessions = sessions
        yield client


@pytest.mark.parametrize("headers", [{}, {"X-Dev-Actor": "desconocido-demo"}, {"X-Dev-Actor": "inactivo-demo"}, {"X-Dev-Actor": ""}, {"X-Role": "supervisor-demo"}, {"X-Dev-Actor": "x" * 101}, [("X-Dev-Actor", "consulta-demo"), ("X-Dev-Actor", "supervisor-demo")]])
def test_rejected_identity_same_public_error(sessions, headers):
    with api(sessions) as client:
        response = client.get("/api/v1/identity/me", headers=headers)
        assert response.status_code == 401
        assert response.json()["error"] == {"code": "IDENTITY_REQUIRED", "message": "Identidad requerida", "details": []}
        assert response.json()["request_id"] == response.headers["X-Request-ID"]


@pytest.mark.parametrize("key", ROLE_PERMISSIONS)
def test_actor_effective_permissions_and_all_operations(sessions, key):
    with api(sessions) as client:
        headers = {"X-Dev-Actor": key, "X-Role": "supervisor-demo", "X-Permissions": "audit.read"}
        response = client.get("/api/v1/identity/me", headers=headers)
        assert response.status_code == 200
        assert set(response.json()["permissions"]) == ROLE_PERMISSIONS[key]
        for operation, required in OPERATION_PERMISSIONS.items():
            result = client.get("/probe/" + operation, headers=headers)
            expected = 200 if set(required).issubset(ROLE_PERMISSIONS[key]) else 403
            assert result.status_code == expected, operation
            if expected == 403:
                assert result.json()["error"]["code"] == "PERMISSION_DENIED"
        projected = client.get("/projection", headers=headers).json()
        expected_fields = PATIENT_BASIC + (PATIENT_DEMOGRAPHICS if key != "consulta-demo" else ())
        assert set(projected) == set(expected_fields)


def test_changes_to_status_and_permissions_apply_on_next_request(sessions):
    with api(sessions) as client:
        headers = {"X-Dev-Actor": "supervisor-demo"}
        first = client.get("/api/v1/identity/me", headers=headers)
        assert first.status_code == 200
        with sessions.begin() as session:
            role_id = session.scalar(select(Role.id).where(Role.code == "supervisor-demo"))
            permission_id = session.scalar(select(Permission.id).where(Permission.code == "audit.read"))
            session.execute(delete(RolePermission).where(RolePermission.role_id == role_id, RolePermission.permission_id == permission_id))
        assert client.get("/probe/audit.read", headers=headers).status_code == 403
        with sessions.begin() as session:
            session.execute(update(User).where(User.actor_key == "supervisor-demo").values(status="inactive"))
        assert client.get("/api/v1/identity/me", headers=headers).status_code == 401


def test_provider_reference_cannot_be_selected_as_development_actor(sessions):
    with sessions.begin() as session:
        session.add(User(actor_key="external-demo", provider="future-provider", subject="ficticio"))
    with api(sessions) as client:
        assert client.get("/api/v1/identity/me", headers={"X-Dev-Actor": "external-demo"}).status_code == 401


def test_seed_idempotent_preserves_ids_suspensions_and_unrelated_rows(sessions):
    settings = Settings(app_env="test")
    with sessions.begin() as session:
        before = {u.actor_key: u.id for u in session.scalars(select(User).where(User.actor_key.in_(ACTOR_ROLES)))}
        session.execute(update(User).where(User.actor_key == "admision-demo").values(status="inactive"))
        unrelated = User(actor_key=str(uuid4()), provider="development", subject=str(uuid4()))
        session.add(unrelated)
        session.flush()
        unrelated_id = unrelated.id
    for _ in range(2):
        with sessions() as session:
            assert seed_local_identity(session, settings) == {"actors": 4, "roles": 3, "permissions": 8}
    with sessions() as session:
        assert before == {u.actor_key: u.id for u in session.scalars(select(User).where(User.actor_key.in_(ACTOR_ROLES)))}
        assert session.scalar(select(User.status).where(User.actor_key == "admision-demo")) == "inactive"
        assert session.get(User, unrelated_id) is not None
        for code, expected in ROLE_PERMISSIONS.items():
            actual = set(session.scalars(select(Permission.code).join(RolePermission).join(Role).where(Role.code == code)))
            assert actual == expected


@pytest.mark.parametrize("drift", ["role", "identity", "extra_role", "inactive_actor"])
def test_seed_rejects_incompatible_data_atomically(sessions, drift):
    with sessions.begin() as session:
        role = session.scalar(select(Role).where(Role.code == "consulta-demo"))
        if drift == "role":
            permission = session.scalar(select(Permission).where(Permission.code == "audit.read"))
            session.add(RolePermission(role_id=role.id, permission_id=permission.id))
        elif drift == "identity":
            session.execute(update(User).where(User.actor_key == "consulta-demo").values(provider="future-provider"))
        elif drift == "extra_role":
            user_id = session.scalar(select(User.id).where(User.actor_key == "consulta-demo"))
            supervisor_id = session.scalar(select(Role.id).where(Role.code == "supervisor-demo"))
            session.add(UserRole(user_id=user_id, role_id=supervisor_id))
        else:
            session.execute(update(User).where(User.actor_key == "inactivo-demo").values(status="active"))
        # Restauración que el seed intentará antes de detectar la discrepancia.
        admission = session.scalar(select(Role.id).where(Role.code == "admision-demo"))
        search = session.scalar(select(Permission.id).where(Permission.code == "patients.search"))
        session.execute(delete(RolePermission).where(RolePermission.role_id == admission, RolePermission.permission_id == search))
    with sessions() as session:
        with pytest.raises(SeedError):
            seed_local_identity(session, Settings(app_env="test"))
        assert session.get(RolePermission, (admission, search)) is None


def test_seed_production_rejected_without_querying_database(sessions):
    with sessions() as session:
        with pytest.raises(SeedError):
            seed_local_identity(session, Settings(app_env="production", dev_identity_enabled=False))
        assert not session.in_transaction()
