"""Entrega V1: preparación, base nueva, HTTP, reinicio y diagnóstico local.

Reinicia sólo PostgreSQL de este proyecto; conserva todas las bases y datos.
Requiere el venv instalado, Docker y configuración local con identidad apagada.
"""
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import socket
import subprocess
import sys
import tempfile
import time
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
from verify_phase2 import await_live, compose


def run(*args, env=None, **kwargs):
    return subprocess.run(args, cwd=ROOT, env=env, check=True, **kwargs)


def snapshot():
    result = {}
    for environment in ("development", "test"):
        db = Database(Settings(app_env=environment))
        try:
            with db.engine.connect() as connection:
                rows = {}
                for table in sorted(inspect(connection).get_table_names()):
                    rows[table] = sorted(json.dumps(dict(row), sort_keys=True, default=str)
                        for row in connection.execute(text(f'SELECT * FROM "{table}"')).mappings())
                sequences = connection.execute(text(
                    "SELECT sequencename, last_value FROM pg_sequences WHERE schemaname='public' ORDER BY sequencename"
                )).all()
                payload = json.dumps([rows, [list(row) for row in sequences]], sort_keys=True)
                result[environment] = {"sha256": hashlib.sha256(payload.encode()).hexdigest(),
                    "counts": {table: len(data) for table, data in rows.items()}}
        finally:
            db.dispose()
    return result


def new_database(settings):
    name = "hospital_v1_validation_" + uuid4().hex
    # Nombre generado internamente; sin credenciales en argv ni salida.
    sql = (f'CREATE DATABASE "{name}" OWNER hospital_dev;\n'
           f'REVOKE CONNECT ON DATABASE "{name}" FROM PUBLIC;\n'
           f'GRANT CONNECT ON DATABASE "{name}" TO hospital_dev;\n')
    run("docker", "compose", "--env-file", "backend/.env", "exec", "-T", "postgres",
        "psql", "-U", "postgres", "-d", "postgres", "-v", "ON_ERROR_STOP=1", input=sql, text=True)
    url = make_url(settings.database_url.get_secret_value()).set(database=name).render_as_string(hide_password=False)
    # production sólo libera la restricción de nombre hospital_dev/test para esta
    # base aislada local. No inicia API, identidad ni semilla en este modo.
    isolated = Settings(app_env="production", database_url=url, dev_identity_enabled=False)
    db = Database(isolated)
    try:
        assert inspect(db.engine).get_table_names() == []
        env = {**os.environ, "APP_ENV": "production", "DEV_IDENTITY_ENABLED": "false", "DATABASE_URL": url}
        for arguments in (("upgrade", "head"), ("upgrade", "head"), ("check",)):
            run(sys.executable, "-m", "alembic", "-c", "backend/alembic.ini", *arguments, env=env)
        with db.engine.connect() as connection:
            revision = connection.scalar(text("SELECT version_num FROM alembic_version"))
            assert revision == "0004"
        reference = Database(Settings(app_env="test"))
        try:
            tables = sorted(inspect(db.engine).get_table_names())
            assert tables == sorted(inspect(reference.engine).get_table_names())
        finally:
            reference.dispose()
        return {"name": name, "tables_before": [], "tables_after": tables, "revision": revision,
                "upgrade_repeated": True, "model_check": True, "retained": True, "loopback_only": True}
    finally:
        db.dispose()


def start_api(enabled, logs):
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    process = subprocess.Popen([sys.executable, "-m", "uvicorn", "hospital.main:create_app", "--factory",
        "--app-dir", "backend/src", "--host", "127.0.0.1", "--port", str(port), "--no-access-log"], cwd=ROOT,
        env={**os.environ, "APP_ENV": "test", "DEV_IDENTITY_ENABLED": str(enabled).lower()}, stdout=logs, stderr=logs)
    return process, httpx.Client(base_url=f"http://127.0.0.1:{port}", trust_env=False, timeout=10)


def stop_api(process):
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def create_patient(client, key, headers):
    search = client.get("/api/v1/patients", headers=headers,
        params={"identifier_system": "TEST", "identifier_value": key})
    assert search.status_code == 200 and search.json()["items"] == []
    response = client.post("/api/v1/patients", headers=headers, json={
        "search_id": search.json()["search_id"], "identity_status": "provisional",
        "given_names": "Persona ficticia V1 validación", "family_name": key,
        "identifiers": [{"system": "TEST", "value": key}]})
    assert response.status_code == 201
    return response


def main():
    settings = load_settings()
    assert settings.app_env in {"development", "test"} and not settings.dev_identity_enabled
    report = {"phase": "V1-07", "date_utc": datetime.now(timezone.utc).isoformat()}
    before = snapshot()
    config = ROOT / "backend/.env"
    config_hash = hashlib.sha256(config.read_bytes()).hexdigest()
    config_mode = config.stat().st_mode & 0o777
    for _ in range(2):
        run(sys.executable, "backend/scripts/prepare_local.py")
        assert snapshot() == before
        assert hashlib.sha256(config.read_bytes()).hexdigest() == config_hash
        assert config.stat().st_mode & 0o777 == config_mode == 0o600
    report["preparation"] = {"runs": 2, "all_rows_and_sequences_unchanged": True,
        "env_unchanged": True, "env_mode": "600", "snapshots": before}
    report["fresh_database"] = new_database(settings)
    with tempfile.TemporaryDirectory(prefix="reimbow-phase7-") as directory:
        junit = Path(directory) / "pytest.xml"
        run(sys.executable, "-m", "pytest", "-q", "-c", "backend/pyproject.toml", "backend/tests", f"--junitxml={junit}")
        suite = ET.parse(junit).getroot().find("testsuite")
        report["pytest"] = {key: int(suite.attrib[key]) for key in ("tests", "failures", "errors", "skipped")}
        assert report["pytest"]["skipped"] == 0

    with tempfile.TemporaryFile(mode="w+") as logs:
        process, client = start_api(False, logs)
        try:
            with client:
                await_live(client, process)
                assert client.get("/api/v1/identity/me", headers={"X-Dev-Actor": "supervisor-demo"}).status_code == 401
                assert client.get("/api/v1/health/ready").status_code == 200
        finally:
            stop_api(process)
        report["disabled_identity"] = {"explicit_demo_actor": 401, "ready": 200}
        process, client = start_api(True, logs)
        stopped = False
        db = Database(Settings(app_env="test"))
        try:
            with client:
                await_live(client, process)
                headers = {"X-Dev-Actor": "admision-demo"}
                read_headers = {"X-Dev-Actor": "consulta-demo"}
                key = "V107-" + uuid4().hex.upper()
                patient_response = create_patient(client, key, headers)
                patient = patient_response.json()
                episode_response = client.post("/api/v1/admissions", headers=headers,
                    json={"patient_id": patient["id"], "type": "emergency"})
                assert episode_response.status_code == 201
                episode = episode_response.json()
                patient_path = f'/api/v1/patients/{patient["id"]}'
                episode_path = f'/api/v1/admissions/{episode["id"]}'
                patient_read = client.get(patient_path, headers=read_headers)
                assert patient_read.status_code == 200
                assert client.get(episode_path, headers=read_headers).json() == episode
                denied = client.post("/api/v1/admissions", headers=read_headers,
                    json={"patient_id": patient["id"], "type": "emergency"})
                assert denied.status_code == 403
                full_before = snapshot()
                # La API y su pool permanecen vivos durante stop/start.
                stopped = True
                compose("stop", "postgres")
                assert client.get("/api/v1/health/live").status_code == 200
                unavailable = client.get("/api/v1/health/ready")
                assert unavailable.status_code == 503
                assert unavailable.json()["error"]["code"] == "DATABASE_UNAVAILABLE"
                compose("up", "-d", "--wait", "postgres")
                stopped = False
                assert snapshot() == full_before
                assert client.get("/api/v1/health/ready").status_code == 200
                assert client.get(patient_path, headers=read_headers).json() == patient_read.json()
                assert client.get(episode_path, headers=read_headers).json() == episode
                assert client.get(patient_path + "/admissions", headers=read_headers).json()["items"] == [episode]
                with db.sessions() as session:
                    for response in (patient_response, episode_response, denied):
                        row = session.scalar(select(AuditEvent).where(
                            AuditEvent.request_id == UUID(response.headers["X-Request-ID"])))
                        assert row is not None and row.result == ("denied" if response.status_code == 403 else "success")
                audit = client.get("/api/v1/audit", headers={"X-Dev-Actor": "supervisor-demo"},
                    params={"resource_id": episode["id"]})
                assert audit.status_code == 200 and audit.json()["total"] >= 1
                report["restart"] = {"same_api_process": process.poll() is None,
                    "database_stopped": {"live": 200, "ready": 503}, "recovered_ready": 200,
                    "all_rows_and_sequences_preserved": True, "patient_id": patient["id"],
                    "admission_id": episode["id"], "http_reads_identical": True, "audit_retained": True,
                    "forbidden_create": 403, "authorized_audit": 200}
                # Dataset exclusivo del diagnóstico, generado mediante el flujo HTTP real.
                print("Preparando 1.000 pacientes ficticios para diagnóstico local…", flush=True)
                patients = [patient]
                started = time.perf_counter()
                for index in range(1, 1000):
                    patients.append(create_patient(client, f"{key}-{index:04d}", headers).json())
                    if index % 200 == 0:
                        print(f"Dataset: {index}/1.000 pacientes", flush=True)
                dataset_seconds = time.perf_counter() - started
                queries = {"folio": {"folio": patient["folio"]},
                    "name": {"name": "Persona ficticia V1 validación"},
                    "TEST": {"identifier_system": "TEST", "identifier_value": key}}
                metrics = {}
                for kind, params in queries.items():
                    timings, errors = [], 0
                    for index in range(110):
                        started = time.perf_counter()
                        response = client.get("/api/v1/patients", params=params, headers=headers)
                        elapsed = (time.perf_counter() - started) * 1000
                        valid = response.status_code == 200 and response.json()["total"] >= 1
                        if kind != "name" and valid:
                            valid = response.json()["items"][0]["id"] == patient["id"]
                        if index >= 10:
                            timings.append(elapsed)
                            errors += int(not valid)
                        else:
                            assert valid
                    ordered = sorted(timings)
                    metrics[kind] = {"samples": 100, "warmup": 10, "errors": errors,
                        "p50_ms": round(ordered[math.ceil(.50 * len(ordered)) - 1], 3),
                        "p95_ms": round(ordered[math.ceil(.95 * len(ordered)) - 1], 3),
                        "max_ms": round(max(ordered), 3), "samples_ms": [round(t, 3) for t in timings]}
                    assert errors == 0
                with db.sessions() as session:
                    version = session.scalar(text("SHOW server_version"))
                    total = session.scalar(text("SELECT count(*) FROM patients"))
                report["performance"] = {"dataset_patients": len(patients), "total_test_patients": total,
                    "dataset_creation_seconds": round(dataset_seconds, 3), "concurrency": 1,
                    "transport": "HTTP loopback, Uvicorn 1 worker, SQLAlchemy sync pool 5+5, audit enabled",
                    "percentiles": "nearest rank", "queries": metrics, "python": platform.python_version(),
                    "platform": platform.platform(), "cpu_count": os.cpu_count(),
                    "cpu_model": next((line.split(':', 1)[1].strip() for line in Path('/proc/cpuinfo').read_text().splitlines()
                        if line.startswith('model name')), 'unknown'),
                    "memory_total": next(line for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemTotal:')),
                    "postgresql_version": version, "sla": None, "production_capacity_validated": False}
        finally:
            if stopped:
                compose("up", "-d", "--wait", "postgres")
            stop_api(process)
            db.dispose()
        logs.seek(0)
        output = logs.read()
        assert "Traceback" not in output and key not in output
        for secret in (settings.database_url, settings.test_database_url):
            assert make_url(secret.get_secret_value()).password not in output
        report["technical_logs_secrets_exposed"] = False
    report["default_identity_enabled"] = load_settings().dev_identity_enabled
    assert report["default_identity_enabled"] is False
    report["temporary_api_processes_stopped"] = True
    target = ROOT / "docs/evidencia/v1-07-resultados.json"
    target.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print("V1-07 verificada. Evidencia: docs/evidencia/v1-07-resultados.json")


if __name__ == "__main__":
    main()
