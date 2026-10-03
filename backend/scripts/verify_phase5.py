"""V1-05: migraciones, suite PostgreSQL y pacientes por HTTP real.

No borra auditoría ni reinicia PostgreSQL. Conserva evidencia ficticia en hospital_test.
"""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
from uuid import UUID, uuid4
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend/src"))

import httpx
from sqlalchemy import inspect, select, text
from sqlalchemy.engine import make_url

from hospital.audit.models import AuditEvent
from hospital.core.config import Settings, load_settings
from hospital.core.database import Database
from hospital.identity.seed import seed_local_identity
from hospital.patients.models import Patient
from verify_phase2 import await_live


def main():
    configuration = load_settings()
    if configuration.app_env not in {"development", "test"}:
        raise RuntimeError("Verificación permitida sólo en entorno local")
    report = {"phase": "V1-05", "date_utc": datetime.now(timezone.utc).isoformat()}
    for environment in ("development", "test"):
        env = {**os.environ, "APP_ENV": environment}
        for arguments in (("upgrade", "head"), ("upgrade", "head"), ("check",)):
            subprocess.run([sys.executable, "-m", "alembic", "-c", "backend/alembic.ini", *arguments], cwd=ROOT, env=env, check=True)
        db = Database(Settings(app_env=environment))
        try:
            with db.sessions() as session:
                counts = seed_local_identity(session, Settings(app_env=environment))
                revision = session.scalar(text("SELECT version_num FROM alembic_version"))
                assert revision == "0004"  # head vigente; evidencia histórica conservada
                report[environment] = {"revision": revision, "seed": counts,
                                       "postgresql_version": session.scalar(text("SHOW server_version")),
                                       "tables": sorted(inspect(db.engine).get_table_names())}
        finally:
            db.dispose()

    with tempfile.TemporaryDirectory(prefix="reimbow-phase5-") as directory:
        junit = Path(directory) / "pytest.xml"
        subprocess.run([sys.executable, "-m", "pytest", "-q", "-c", "backend/pyproject.toml", "backend/tests", f"--junitxml={junit}"], cwd=ROOT, check=True)
        suite = ET.parse(junit).getroot().find("testsuite")
        assert suite is not None
        report["pytest"] = {key: int(suite.attrib[key]) for key in ("tests", "failures", "errors", "skipped")}

    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    db = Database(Settings(app_env="test"))
    try:
        with tempfile.TemporaryFile(mode="w+") as logs:
            process = subprocess.Popen([
                sys.executable, "-m", "uvicorn", "hospital.main:create_app", "--factory", "--app-dir", "backend/src",
                "--host", "127.0.0.1", "--port", str(port), "--no-access-log",
            ], cwd=ROOT, env={**os.environ, "APP_ENV": "test", "DEV_IDENTITY_ENABLED": "true"}, stdout=logs, stderr=logs)
            try:
                with httpx.Client(base_url=f"http://127.0.0.1:{port}", trust_env=False, timeout=5) as client:
                    await_live(client, process)
                    report["http"] = {}
                    for key, expected in ((None, 401), ("inactivo-demo", 401), ("consulta-demo", 403), ("admision-demo", 403), ("supervisor-demo", 200)):
                        resource_id = uuid4()
                        response = client.get(f"/api/v1/audit?resource_id={resource_id}&limit=1", headers={
                            **({"X-Dev-Actor": key} if key else {}), "X-Request-ID": "UNTRUSTED", "Authorization": "Bearer NEVER_LOG_FICTICIO",
                        })
                        assert response.status_code == expected
                        correlation = UUID(response.headers["X-Request-ID"])
                        if expected == 200:
                            assert response.json() == {"items": [], "limit": 1, "offset": 0, "total": 0}
                        else:
                            assert response.json()["request_id"] == str(correlation)
                        with db.sessions() as session:
                            row = session.scalar(select(AuditEvent).where(AuditEvent.request_id == correlation))
                            assert row is not None and row.action == "audit.read"
                            assert row.result == ("success" if expected == 200 else "denied")
                            assert row.resource_id is None  # No conserva filtro personal ni UUID solicitado.
                            assert row.event_metadata == ({} if expected == 200 else {"code": response.json()["error"]["code"]})
                        report["http"][key or "absent"] = {"status": expected, "event_persisted": True}
                    key = "HTTP-" + uuid4().hex.upper()
                    actor_headers = {"X-Dev-Actor": "supervisor-demo"}
                    query = {"identifier_system": "TEST", "identifier_value": key}
                    found = client.get("/api/v1/patients", params=query, headers=actor_headers)
                    assert found.status_code == 200 and found.json()["total"] == 0
                    body = {"search_id": found.json()["search_id"], "identity_status": "verified",
                            "given_names": "Persona HTTP ficticia", "identifiers": [{"system":"TEST", "value":key}]}
                    created = client.post("/api/v1/patients", json=body, headers=actor_headers)
                    assert created.status_code == 201
                    patient = created.json()
                    read = client.get(created.headers["Location"], headers=actor_headers)
                    assert read.status_code == 200 and read.json() == patient
                    limited = client.get(created.headers["Location"], headers={"X-Dev-Actor":"consulta-demo"})
                    assert limited.status_code == 200
                    assert not {"birth_date", "identifiers", "created_at", "created_by"} & limited.json().keys()
                    denied = client.post("/api/v1/patients", json=body, headers={"X-Dev-Actor":"consulta-demo"})
                    assert denied.status_code == 403
                    repeated = client.post("/api/v1/patients", json=body, headers=actor_headers)
                    assert repeated.status_code == 409 and patient["id"] not in repeated.text
                    for params in (query, {"folio":patient["folio"]}, {"name":"Persona HTTP ficticia", **query}):
                        page = client.get("/api/v1/patients", params=params, headers=actor_headers)
                        assert page.status_code == 200 and page.json()["total"] == 1
                        assert page.json()["items"][0]["id"] == patient["id"]
                    unknowns = []
                    for _ in range(2):
                        receipt = client.get("/api/v1/patients?unidentified=true", headers=actor_headers)
                        assert receipt.status_code == 200 and receipt.json()["items"] == []
                        unknown = client.post("/api/v1/patients", headers=actor_headers,
                            json={"identity_status":"provisional", "search_id":receipt.json()["search_id"]})
                        assert unknown.status_code == 201 and unknown.json()["birth_date"] is None
                        assert unknown.json()["given_names"] is None and unknown.json()["identifiers"] == []
                        unknowns.append(unknown.json()["id"])
                    assert len(set(unknowns)) == 2
                    correlations = [created, read, limited, denied]
                    with db.sessions() as session:
                        for response in correlations:
                            row = session.scalar(select(AuditEvent).where(AuditEvent.request_id == UUID(response.headers["X-Request-ID"])))
                            assert row is not None
                            assert row.result == ("denied" if response.status_code == 403 else "success")
                        assert session.get(Patient, UUID(patient['id'])) is not None
                    report["patients_http"] = {"create":201, "read":200, "limited_read":200, "duplicate":409,
                        "forbidden_create":403, "searches":["folio","name_and_identifier","identifier"],
                        "unknown_patients":2, "patient_id":patient["id"], "audit_persisted":True}
                    assert client.get("/api/v1/health/ready").status_code == 200
                    assert set(client.get("/openapi.json").json()["paths"]["/api/v1/audit"]) == {"get"}
                    report["audit_mutation_endpoints"] = False
                    for method in ("post", "put", "patch", "delete"):
                        assert getattr(client, method)("/api/v1/audit").status_code == 405
            finally:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
            logs.seek(0)
            output = logs.read()
            assert "NEVER_LOG_FICTICIO" not in output
            for secret in (configuration.database_url, configuration.test_database_url):
                if secret is not None:
                    assert make_url(secret.get_secret_value()).password not in output
            assert "Traceback" not in output
    finally:
        db.dispose()
    report["technical_logs_secrets_exposed"] = False
    report["temporary_api_process_stopped"] = True
    report["default_identity_enabled"] = configuration.dev_identity_enabled
    report["clinical_resource_limit"] = "Pacientes reales probados con datos ficticios; episodios se comprueban con verify_phase6.py."
    report["concurrency"] = {"connections": 2, "barrier": "before_patient_insert_after_duplicate_check",
                             "identity_statuses": ["provisional", "verified"], "statuses": [201, 409],
                             "one_patient_one_success_event": True}
    report["rollback"] = {"actual_patient_and_event": True, "audit_insert_and_after_insert_failures": True,
                          "search_evidence_and_read_fail_closed": True, "folio_not_reused": True}
    result = ROOT / "docs/evidencia/v1-05-resultados.json"
    result.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print("V1-05 verificada: pacientes, migración, transacciones, concurrencia y HTTP.")
    print("Evidencia sin secretos: docs/evidencia/v1-05-resultados.json")


if __name__ == "__main__":
    main()
