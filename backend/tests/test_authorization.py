from uuid import uuid4

import pytest
from fastapi import Depends
from fastapi.testclient import TestClient
from pydantic import ValidationError

from hospital.authorization.projections import ADMISSION_FIELDS, PATIENT_BASIC, PATIENT_DEMOGRAPHICS, admission_projection, patient_projection
from hospital.authorization.service import Actor, OPERATION_PERMISSIONS, authorize
from hospital.core.config import Settings
from hospital.core.errors import ApplicationError
from hospital.identity.dependencies import permitted
from hospital.main import create_app

DEV = "postgresql+psycopg://hospital_dev:FAKE@127.0.0.1:1/hospital_dev"


@pytest.mark.parametrize("operation,required", OPERATION_PERMISSIONS.items())
def test_every_permission_is_required(operation, required):
    authorize(Actor(uuid4(), "ficticio", frozenset(required)), operation)
    for missing in required:
        with pytest.raises(ApplicationError) as captured:
            authorize(Actor(uuid4(), "ficticio", frozenset(set(required) - {missing})), operation)
        assert captured.value.status == 403


def test_patient_projection_omits_sensitive_and_unknown_fields():
    data = dict.fromkeys(PATIENT_BASIC + PATIENT_DEMOGRAPHICS + ("internal_secret",), "ficticio")
    limited = Actor(uuid4(), "ficticio", frozenset({"patients.read", "patients.search"}))
    for operation in ("patients.read", "patients.search"):
        assert set(patient_projection(limited, data, operation=operation)) == set(PATIENT_BASIC)
    full = Actor(uuid4(), "ficticio", limited.permissions | {"patients.read_demographics"})
    assert set(patient_projection(full, data)) == set(PATIENT_BASIC + PATIENT_DEMOGRAPHICS)
    with pytest.raises(ApplicationError):
        patient_projection(Actor(uuid4(), "ficticio", frozenset({"patients.read_demographics"})), data)


def test_admission_projection_never_includes_patient_demographics():
    data = dict.fromkeys(ADMISSION_FIELDS + ("birth_date", "identifiers"), "ficticio")
    actor = Actor(uuid4(), "ficticio", frozenset({"admissions.read", "patients.read_demographics"}))
    assert set(admission_projection(actor, data)) == set(ADMISSION_FIELDS)


@pytest.mark.parametrize("environment", ["development", "production"])
def test_disabled_identity_rejects_even_known_actor_without_database(environment):
    app = create_app(Settings(_env_file=None, database_url=DEV, app_env=environment, dev_identity_enabled=False))
    with TestClient(app) as client:
        response = client.get("/api/v1/identity/me", headers={"X-Dev-Actor": "supervisor-demo"})
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "IDENTITY_REQUIRED"
        assert client.get("/api/v1/health/live").status_code == 200


def test_production_app_cannot_be_created_with_simulated_provider(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DEV_IDENTITY_ENABLED", "true")
    from hospital.core.config import ConfigurationError
    with pytest.raises(ConfigurationError):
        create_app()
    with pytest.raises(ValidationError):
        Settings(_env_file=None, app_env="production", dev_identity_enabled=True, database_url=DEV)


def test_route_guard_checks_identity_before_resource_or_parameter_validation():
    app = create_app(Settings(_env_file=None, database_url=DEV, dev_identity_enabled=False))

    @app.get("/probe/{resource_id}")
    def probe(resource_id: int, actor=Depends(permitted("audit.read"))):
        pytest.fail("Recurso leído sin autorización")

    with TestClient(app) as client:
        assert client.get("/probe/not-an-int").status_code == 401
