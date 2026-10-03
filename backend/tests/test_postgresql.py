from pathlib import Path
from uuid import uuid4

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import inspect, select, text
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from hospital.authorization.models import Permission, Role, RolePermission, UserRole
from hospital.core.config import Settings
from hospital.core.database import Database
from hospital.identity.models import User
from hospital.main import create_app

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def database():
    configuration = Settings(app_env="test")
    db = Database(configuration)
    assert make_url(configuration.connection_url).database == "hospital_test"
    with db.engine.connect() as connection:
        assert connection.scalar(text("SELECT current_database()")) == "hospital_test"
    yield db
    db.dispose()


@pytest.fixture
def session(database):
    # Todas las filas de prueba se revierten, incluidos commits de un servicio.
    with database.engine.connect() as connection:
        outer = connection.begin()
        with Session(bind=connection, join_transaction_mode="create_savepoint") as session:
            yield session
        outer.rollback()


def test_migration_idempotent_and_matches_models(database, monkeypatch):
    monkeypatch.setenv("APP_ENV", "test")
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    command.upgrade(config, "head")
    command.upgrade(config, "head")
    command.check(config)
    assert set(inspect(database.engine).get_table_names()) == {
        "alembic_version", "institutional_users", "roles", "permissions", "user_roles", "role_permissions", "audit_events", "patients", "patient_identifiers", "patient_searches", "admissions",
        "patient_administrative_profiles", "patient_administrative_items", "patient_identity_verifications", "patient_verification_evidence", "admission_sites", "admission_services", "admission_intakes", "idempotency_records"
    }
    with database.engine.connect() as connection:
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "0006"


def test_ready_against_real_postgresql(database):
    with TestClient(create_app(Settings(app_env="test"))) as client:
        assert client.get("/api/v1/health/ready").json() == {"status": "ready"}


def test_user_defaults_and_timezone(session):
    user = User(actor_key=str(uuid4()), provider="development", subject=str(uuid4()))
    session.add(user)
    session.flush()
    assert user.status == "active"
    assert user.created_at.tzinfo is not None
    assert user.id is not None


@pytest.mark.parametrize("duplicate", ["actor", "reference"])
def test_identity_uniqueness(session, duplicate):
    actor, subject = str(uuid4()), str(uuid4())
    session.add(User(actor_key=actor, provider="development", subject=subject))
    session.flush()
    session.add(User(actor_key=actor if duplicate == "actor" else str(uuid4()),
                     provider="development", subject=subject if duplicate == "reference" else str(uuid4())))
    with pytest.raises(IntegrityError):
        session.flush()
    session.rollback()


@pytest.mark.parametrize("status,actor", [("invalid", "fake"), ("active", " ")])
def test_user_checks(session, status, actor):
    session.add(User(actor_key=actor, provider="development", subject=str(uuid4()), status=status))
    with pytest.raises(IntegrityError):
        session.flush()
    session.rollback()


def test_assignment_uniqueness_and_restricted_foreign_keys(session):
    user = User(actor_key=str(uuid4()), provider="development", subject=str(uuid4()))
    role, permission = Role(code=str(uuid4())), Permission(code=str(uuid4()))
    session.add_all([user, role, permission])
    session.flush()
    session.add_all([UserRole(user_id=user.id, role_id=role.id),
                     RolePermission(role_id=role.id, permission_id=permission.id)])
    session.flush()
    with pytest.raises(IntegrityError):
        with session.begin_nested():
            session.execute(text("INSERT INTO user_roles (user_id,role_id) VALUES (:user,:role)"),
                            {"user": user.id, "role": role.id})
    with pytest.raises(IntegrityError):
        with session.begin_nested():
            session.delete(role)
            session.flush()


def test_uncommitted_work_is_rolled_back(database):
    code = str(uuid4())
    with database.sessions() as session:
        session.add(Role(code=code))
        session.flush()
    with database.sessions() as session:
        assert session.scalar(select(Role).where(Role.code == code)) is None


def test_database_users_are_isolated(database):
    from sqlalchemy import create_engine
    url = make_url(Settings(app_env="test").connection_url).set(database="hospital_dev")
    engine = create_engine(url, connect_args={"connect_timeout": 2}, hide_parameters=True)
    try:
        with pytest.raises(OperationalError):
            with engine.connect():
                pass
    finally:
        engine.dispose()
