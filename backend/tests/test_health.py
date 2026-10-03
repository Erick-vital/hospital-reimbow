from uuid import UUID

from fastapi.testclient import TestClient

from hospital.core.config import Settings
from hospital.main import create_app


def test_live_and_sanitized_ready_when_database_is_unreachable(caplog):
    secret = "FAKE_SECRET_NEVER_LOGGED"
    settings = Settings(_env_file=None, app_env="development", database_url=
        f"postgresql+psycopg://hospital_dev:{secret}@127.0.0.1:1/hospital_dev")
    with TestClient(create_app(settings)) as client:
        live = client.get("/api/v1/health/live", headers={"X-Request-ID": "untrusted"})
        assert live.status_code == 200 and live.json() == {"status": "alive"}
        UUID(live.headers["X-Request-ID"])
        ready = client.get("/api/v1/health/ready")
        assert ready.status_code == 503
        body = ready.json()
        assert body["error"]["code"] == "DATABASE_UNAVAILABLE"
        assert body["request_id"] == ready.headers["X-Request-ID"]
        assert secret not in ready.text + caplog.text
        assert "postgresql" not in ready.text
        assert client.get("/api/v1/health/live").status_code == 200


def test_current_routes_available():
    settings = Settings(_env_file=None, database_url=
        "postgresql+psycopg://hospital_dev:FAKE@127.0.0.1:1/hospital_dev")
    with TestClient(create_app(settings)) as client:
        paths = client.get("/openapi.json").json()["paths"]
        assert {p for p in paths if p.startswith('/api/v1/')} == {"/api/v1/health/live", "/api/v1/health/ready", "/api/v1/identity/me", "/api/v1/audit", "/api/v1/patients", "/api/v1/patients/{patient_id}", "/api/v1/admissions", "/api/v1/admissions/{admission_id}", "/api/v1/patients/{patient_id}/admissions"}
        assert {p for p in paths if p.startswith('/api/v2/')} == {'/api/v2/patients', '/api/v2/patients/{patient_id}', '/api/v2/admissions/{admission_id}', '/api/v2/patients/{patient_id}/admissions', '/api/v2/catalogs/sites', '/api/v2/catalogs/services'}
        response = client.get("/api/v1/patients")
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "IDENTITY_REQUIRED"
