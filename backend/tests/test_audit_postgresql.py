from uuid import UUID, uuid4

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import event, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from hospital.audit.models import AuditEvent
from hospital.audit.service import list_events, record_denial, record_success
from hospital.authorization.models import Role
from hospital.authorization.service import Actor
from hospital.core.config import Settings
from hospital.core.database import Database
from hospital.identity.models import User
from hospital.identity.seed import ROLE_PERMISSIONS
from hospital.main import create_app

pytestmark = pytest.mark.integration


@pytest.fixture
def database():
    db = Database(Settings(app_env="test"))
    with db.engine.connect() as connection:
        assert connection.scalar(text("SELECT current_database()")) == "hospital_test"
    yield db
    db.dispose()


@pytest.fixture
def sessions(database):
    with database.engine.connect() as connection:
        outer = connection.begin()
        factory = sessionmaker(bind=connection, join_transaction_mode="create_savepoint", expire_on_commit=False)
        yield factory
        outer.rollback()


@pytest.fixture
def actor(database):
    # Semilla previamente preparada y confirmada; visible en conexiones independientes.
    with database.sessions() as session:
        user = session.scalar(select(User).where(User.actor_key == "supervisor-demo", User.status == "active"))
        assert user is not None, "Ejecutar seed_identity.py con APP_ENV=test"
        return Actor(user.id, user.actor_key, ROLE_PERMISSIONS["supervisor-demo"])


def creation_values(action, resource_id, actor):
    base = {"id": resource_id, "folio": "FICTICIO", "created_at": "2026-10-02T00:00:00Z", "created_by": actor.id}
    if action == "patients.create":
        base.update(identity_status="provisional", given_names="Ficticio", family_name=None,
                    second_family_name=None, birth_date=None, identifiers=[{"system": "TEST", "value": "FICTICIO", "secret": "NO_GUARDAR"}])
    else:
        base.update(patient_id=uuid4(), type="emergency", status="open")
    base["password"] = "NO_GUARDAR"
    return base


@pytest.mark.parametrize("action", ["patients.create", "admissions.create"])
@pytest.mark.parametrize("failure", ["audit_insert", "after_audit_insert"])
def test_resource_and_success_event_rollback_together(database, actor, action, failure):
    resource_id, correlation, code = uuid4(), uuid4(), str(uuid4())
    # Role es un recurso ficticio de prueba del límite transaccional: no anticipa
    # entidades clínicas de V1-05/06 ni publica rutas incompletas.
    with database.sessions() as session:
        with pytest.raises((IntegrityError, RuntimeError)):
            with session.begin():
                session.add(Role(id=resource_id, code=code))
                session.flush()
                record_success(session, actor=actor, action=action,
                               request_id=None if failure == "audit_insert" else correlation,
                               resource_id=resource_id, new_values=creation_values(action, resource_id, actor))
                if failure == "after_audit_insert":
                    raise RuntimeError("Fallo ficticio después de insertar evento")
    with database.sessions() as observer:
        assert observer.get(Role, resource_id) is None
        assert observer.scalar(select(AuditEvent.id).where(AuditEvent.resource_id == resource_id)) is None


@pytest.mark.parametrize("action", ["patients.create", "admissions.create"])
def test_success_snapshot_and_query_projection(sessions, actor, action):
    resource_id, correlation = uuid4(), uuid4()
    with sessions.begin() as session:
        event_row = record_success(session, actor=actor, action=action, request_id=correlation,
                                   resource_id=resource_id, new_values=creation_values(action, resource_id, actor))
        event_id = event_row.id
        assert event_row.created_at.tzinfo is not None
    with sessions() as session:
        page = list_events(session, actor=actor, request_id=uuid4(), resource_id=resource_id, action=action)
        assert page["total"] == 1
        item = page["items"][0]
        assert item["id"] == event_id and item["request_id"] == correlation
        assert item["metadata"]["old"] is None
        assert "NO_GUARDAR" not in str(item)
        assert item["metadata"]["new"]["id"] == str(resource_id)


@pytest.mark.parametrize("action", ["patients.search", "patients.read", "admissions.read", "admissions.list"])
def test_sensitive_reads_store_only_resource_and_correlation(sessions, actor, action):
    with sessions.begin() as session:
        row = record_success(session, actor=actor, action=action, request_id=uuid4())
        assert row.event_metadata == {}
        with pytest.raises(ValueError):
            record_success(session, actor=actor, action=action, request_id=uuid4(), new_values={"name": "NO_GUARDAR"})


def test_success_requires_callers_transaction(database, actor):
    with database.sessions() as session:
        with pytest.raises(RuntimeError):
            record_success(session, actor=actor, action="patients.read", request_id=uuid4())
        assert not session.in_transaction()


def test_denial_commits_on_distinct_connection_while_resource_transaction_is_open(database, actor):
    resource_id, correlation, pids = uuid4(), uuid4(), []

    def observe(connection, cursor, statement, parameters, context, executemany):
        if statement.startswith("INSERT INTO audit_events"):
            pids.append(connection.connection.driver_connection.info.backend_pid)

    event.listen(database.engine, "before_cursor_execute", observe)
    try:
        with database.sessions() as session:
            transaction = session.begin()
            business_pid = session.scalar(text("SELECT pg_backend_pid()"))
            session.add(Role(id=resource_id, code=str(uuid4())))
            session.flush()
            record_denial(database.sessions, actor_id=actor.id, action="patients.create",
                          request_id=correlation, code="PERMISSION_DENIED")
            assert pids and pids[-1] != business_pid
            transaction.rollback()
        with database.sessions() as observer:
            assert observer.get(Role, resource_id) is None
            row = observer.scalar(select(AuditEvent).where(AuditEvent.request_id == correlation))
            assert row is not None and row.result == "denied" and row.actor_id == actor.id
            assert row.resource_id is None and row.event_metadata == {"code": "PERMISSION_DENIED"}
    finally:
        event.remove(database.engine, "before_cursor_execute", observe)


@pytest.mark.parametrize("headers,expected,actor_present", [({}, 401, False), ({"X-Dev-Actor": "inactivo-demo"}, 401, False), ({"X-Dev-Actor": "consulta-demo"}, 403, True)])
def test_http_denials_persist_minimal_event(database, headers, expected, actor_present):
    with TestClient(create_app(Settings(app_env="test", dev_identity_enabled=True))) as client:
        response = client.get("/api/v1/audit?resource_id=" + str(uuid4()), headers={**headers, "X-Request-ID": "NO_CONFIAR", "Authorization": "Bearer SECRETO_FICTICIO"})
    assert response.status_code == expected
    correlation = UUID(response.headers["X-Request-ID"])
    with database.sessions() as session:
        row = session.scalar(select(AuditEvent).where(AuditEvent.request_id == correlation))
        assert row.result == "denied" and row.action == "audit.read"
        assert (row.actor_id is not None) == actor_present
        assert row.resource_id is None
        assert set(row.event_metadata) == {"code"}
        assert "SECRETO" not in str(row.event_metadata)


def test_denial_channel_failure_preserves_response_and_logs_only_code_correlation(caplog):
    settings = Settings(_env_file=None, database_url="postgresql+psycopg://hospital_dev:SECRETO_DB@127.0.0.1:1/hospital_dev")
    with TestClient(create_app(settings)) as client:
        response = client.get("/api/v1/audit?name=PERSONAL_NO_LOG", headers={"Authorization": "Bearer SECRETO_TOKEN", "X-Dev-Actor": "IDENTIDAD_NO_LOG"})
    assert response.status_code == 401
    assert "AUDIT_DENIAL_UNAVAILABLE code=IDENTITY_REQUIRED request_id=" in caplog.text
    for secret in ("SECRETO_DB", "SECRETO_TOKEN", "IDENTIDAD_NO_LOG", "PERSONAL_NO_LOG", "postgresql", "Traceback"):
        assert secret not in caplog.text + response.text


def test_pagination_filtering_and_own_access_not_returned(sessions, actor):
    resource_id = uuid4()
    correlations = [uuid4(), uuid4(), uuid4()]
    with sessions.begin() as session:
        for correlation in correlations:
            record_success(session, actor=actor, action="patients.read", resource_id=resource_id, request_id=correlation)
    with sessions() as session:
        request_id = uuid4()
        first = list_events(session, actor=actor, request_id=request_id, resource_id=resource_id, limit=2)
        assert first["total"] == 3 and len(first["items"]) == 2
        assert [e["request_id"] for e in first["items"]] == correlations[:2]
        assert all(e["request_id"] != request_id for e in first["items"])
    with sessions() as session:
        second = list_events(session, actor=actor, request_id=uuid4(), resource_id=resource_id, offset=2, limit=2)
        assert [e["request_id"] for e in second["items"]] == correlations[2:]
    with sessions() as session:
        empty = list_events(session, actor=actor, request_id=uuid4(), resource_id=resource_id, offset=30)
        assert empty["total"] == 3 and empty["items"] == []
    with sessions() as session:
        correlation = uuid4()
        page = list_events(session, actor=actor, request_id=correlation, action="audit.read", limit=100)
        assert all(e["request_id"] != correlation for e in page["items"])
        assert session.scalar(select(AuditEvent.id).where(AuditEvent.request_id == correlation)) is not None


def test_http_validation_and_no_mutation_endpoints(sessions):
    with TestClient(create_app(Settings(app_env="test", dev_identity_enabled=True))) as client:
        client.app.state.database.sessions = sessions
        headers = {"X-Dev-Actor": "supervisor-demo"}
        for query in ("limit=0", "limit=101", "offset=-1", "resource_id=not-uuid", "action=not-action"):
            assert client.get("/api/v1/audit?" + query, headers=headers).status_code == 422
        assert client.get("/api/v1/audit?limit=1", headers=headers).status_code == 200
        assert set(client.get("/openapi.json").json()["paths"]["/api/v1/audit"]) == {"get"}
        for method in ("post", "put", "patch", "delete"):
            assert getattr(client, method)("/api/v1/audit", headers=headers).status_code == 405


def test_sensitive_read_fails_when_success_audit_fails(sessions, monkeypatch):
    from hospital.audit import service
    original = service.record_success

    def fail(session, **kwargs):
        return original(session, **{**kwargs, "request_id": None})

    monkeypatch.setattr(service, "record_success", fail)
    with TestClient(create_app(Settings(app_env="test", dev_identity_enabled=True))) as client:
        client.app.state.database.sessions = sessions
        response = client.get("/api/v1/audit", headers={"X-Dev-Actor": "supervisor-demo"})
        assert response.status_code == 503
        assert "items" not in response.json()
        with sessions() as observer:
            assert observer.scalar(select(AuditEvent.id).where(AuditEvent.request_id == UUID(response.headers["X-Request-ID"]))) is None


@pytest.mark.parametrize("changes", [
    {"actor_id": None}, {"action": "invalid"}, {"result": "invalid"},
    {"event_metadata": []}, {"resource_type": "invalid"},
    {"result": "denied", "event_metadata": {"name": "FICTICIO"}},
    {"result": "denied", "event_metadata": {"code": "PERMISSION_DENIED"}, "resource_id": uuid4()},
])
def test_database_enforces_audit_integrity(sessions, actor, changes):
    with sessions() as session:
        data = {"actor_id": actor.id, "action": "patients.read", "result": "success", "request_id": uuid4(), "event_metadata": {}}
        data.update(changes)
        with pytest.raises(IntegrityError):
            with session.begin():
                session.add(AuditEvent(**data))
                session.flush()
