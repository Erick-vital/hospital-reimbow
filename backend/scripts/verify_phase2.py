"""Verifica V1-02, reiniciando sólo el PostgreSQL del proyecto y sin borrar datos.

Ejecutar desde la raíz con backend/.venv/bin/python. Requiere Docker y TCP local.
La API temporal usa un puerto libre; PostgreSQL se restaura incluso si falla la prueba.
"""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
from uuid import UUID

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend/src"))

import httpx
from sqlalchemy import inspect, text

from hospital.core.config import Settings, load_settings
from hospital.core.database import Database


def run(arguments, **kwargs):
    return subprocess.run(arguments, cwd=ROOT, check=True, **kwargs)


def compose(*arguments):
    run(["docker", "compose", "--env-file", "backend/.env", *arguments])


def await_live(client, process):
    for _ in range(100):
        if process.poll() is not None:
            raise RuntimeError("La API temporal no arrancó")
        try:
            response = client.get("/api/v1/health/live")
            if response.status_code == 200:
                return
        except httpx.TransportError:
            pass
        time.sleep(0.1)
    raise RuntimeError("Tiempo de arranque agotado")


def main():
    configuration = load_settings()
    if configuration.app_env not in {"development", "test"}:
        raise RuntimeError("Verificación permitida sólo en entorno local")
    report = {"phase": "V1-02", "date_utc": datetime.now(timezone.utc).isoformat()}
    for environment in ("development", "test"):
        settings = Settings(app_env=environment)
        db = Database(settings)
        try:
            before = inspect(db.engine).get_table_names()
            report[environment] = {"tables_before_upgrade": sorted(before)}
            env = {**os.environ, "APP_ENV": environment}
            run([sys.executable, "-m", "alembic", "-c", "backend/alembic.ini", "upgrade", "head"], env=env)
            run([sys.executable, "-m", "alembic", "-c", "backend/alembic.ini", "check"], env=env)
            with db.engine.connect() as connection:
                report[environment]["revision"] = connection.scalar(text("SELECT version_num FROM alembic_version"))
                report[environment]["postgresql_version"] = connection.scalar(text("SHOW server_version"))
            report[environment]["tables_after_upgrade"] = sorted(inspect(db.engine).get_table_names())
        finally:
            db.dispose()

    # Probe ficticia persistente exclusivamente en la base de pruebas.
    db = Database(Settings(app_env="test"))
    try:
        with db.engine.begin() as connection:
            probe = str(connection.scalar(text(
                "INSERT INTO roles (code) VALUES ('phase2-persistence-demo') "
                "ON CONFLICT (code) DO UPDATE SET code=excluded.code RETURNING id")))
    finally:
        db.dispose()

    # Pruebas de integración/configuración no cambian datos de desarrollo.
    run([sys.executable, "-m", "pytest", "-q", "backend/tests", "-c", "backend/pyproject.toml"])
    report["pytest_exit_code"] = 0

    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    with tempfile.TemporaryFile(mode="w+") as logs:
        process = subprocess.Popen([
            sys.executable, "-m", "uvicorn", "hospital.main:create_app", "--factory",
            "--app-dir", "backend/src", "--host", "127.0.0.1", "--port", str(port),
            "--no-access-log",
        ], cwd=ROOT, stdout=logs, stderr=logs, env={**os.environ, "APP_ENV": "development"})
        stopped = False
        try:
            with httpx.Client(base_url=f"http://127.0.0.1:{port}", timeout=10, trust_env=False) as client:
                await_live(client, process)
                ready = client.get("/api/v1/health/ready")
                assert ready.status_code == 200 and ready.json() == {"status": "ready"}
                report["http_before_stop"] = {"live": 200, "ready": ready.status_code}
                # Mantener el mismo proceso API y su pool durante caída y recuperación.
                stopped = True
                compose("stop", "postgres")
                live = client.get("/api/v1/health/live")
                unavailable = client.get("/api/v1/health/ready")
                assert live.status_code == 200 and live.json() == {"status": "alive"}
                assert unavailable.status_code == 503
                assert unavailable.json()["error"]["code"] == "DATABASE_UNAVAILABLE"
                UUID(unavailable.json()["request_id"])
                assert unavailable.json()["request_id"] == unavailable.headers["X-Request-ID"]
                # No exponer URL ni ninguna de las credenciales de ambas bases.
                for secret in (configuration.database_url, configuration.test_database_url):
                    if secret is not None:
                        from sqlalchemy.engine import make_url
                        password = make_url(secret.get_secret_value()).password
                        assert password not in unavailable.text
                assert "postgresql" not in unavailable.text and "Traceback" not in unavailable.text
                report["http_database_stopped"] = {"live": live.status_code, "ready": unavailable.status_code,
                                                  "code": unavailable.json()["error"]["code"], "credentials_exposed": False}
                compose("up", "-d", "--wait", "postgres")
                stopped = False
                recovered = client.get("/api/v1/health/ready")
                assert recovered.status_code == 200
                report["http_after_restart"] = {"live": client.get("/api/v1/health/live").status_code,
                                                "ready": recovered.status_code}
                assert process.poll() is None
        finally:
            if stopped:
                compose("up", "-d", "--wait", "postgres")
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        logs.seek(0)
        technical_logs = logs.read()
        for secret in (configuration.database_url, configuration.test_database_url):
            if secret is not None:
                from sqlalchemy.engine import make_url
                assert make_url(secret.get_secret_value()).password not in technical_logs
        assert "Traceback" not in technical_logs
        report["api_logs_credentials_exposed"] = False

    db = Database(Settings(app_env="test"))
    try:
        with db.engine.connect() as connection:
            retained = str(connection.scalar(text("SELECT id FROM roles WHERE code='phase2-persistence-demo'")))
        assert retained == probe
        report["test_probe_persisted_after_restart"] = True
    finally:
        db.dispose()
    result = ROOT / "docs/evidencia/v1-02-resultados.json"
    result.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print("V1-02 verificada: migraciones, pruebas, HTTP, caída/recuperación y persistencia.")
    print("Evidencia sin credenciales: docs/evidencia/v1-02-resultados.json")


if __name__ == "__main__":
    main()
