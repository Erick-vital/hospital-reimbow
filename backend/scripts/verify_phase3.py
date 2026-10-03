"""V1-03: semilla local, pruebas PostgreSQL y HTTP real, sin reiniciar la base."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
from uuid import UUID
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend/src"))

import httpx
from sqlalchemy import select, text
from sqlalchemy.engine import make_url

from hospital.core.config import Settings, load_settings
from hospital.core.database import Database
from hospital.identity.models import User
from alembic.config import Config
from alembic.script import ScriptDirectory
from hospital.identity.seed import ACTOR_ROLES, ROLE_PERMISSIONS, seed_local_identity
from verify_phase2 import await_live


def main():
    configuration = load_settings()
    if configuration.app_env not in {"development", "test"}:
        raise RuntimeError("Verificación permitida sólo en entorno local")
    head = ScriptDirectory.from_config(Config(str(ROOT / "backend/alembic.ini"))).get_current_head()
    report = {"phase": "V1-03", "date_utc": datetime.now(timezone.utc).isoformat()}
    for environment in ("development", "test"):
        db = Database(Settings(app_env=environment))
        try:
            with db.sessions() as session:
                counts = seed_local_identity(session, Settings(app_env=environment))
                before = {u.actor_key: str(u.id) for u in session.scalars(select(User).where(User.actor_key.in_(ACTOR_ROLES)))}
            with db.sessions() as session:
                seed_local_identity(session, Settings(app_env=environment))
                after = {u.actor_key: str(u.id) for u in session.scalars(select(User).where(User.actor_key.in_(ACTOR_ROLES)))}
                assert before == after
                assert session.scalar(text("SELECT version_num FROM alembic_version")) == head
                report[environment] = {"seed": counts, "stable_actor_ids": True, "revision": head,
                                       "postgresql_version": session.scalar(text("SHOW server_version"))}
        finally:
            db.dispose()

    with tempfile.TemporaryDirectory(prefix="reimbow-phase3-") as directory:
        junit = Path(directory) / "pytest.xml"
        subprocess.run([sys.executable, "-m", "pytest", "-q", "-c", "backend/pyproject.toml", "backend/tests",
                        f"--junitxml={junit}"], cwd=ROOT, check=True)
        suite = ET.parse(junit).getroot().find("testsuite")
        assert suite is not None
        report["pytest"] = {key: int(suite.attrib[key]) for key in ("tests", "failures", "errors", "skipped")}

    report["http"] = {}
    for environment, enabled in (("development", True), ("development", False), ("production", False)):
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        env = {**os.environ, "APP_ENV": environment, "DEV_IDENTITY_ENABLED": str(enabled).lower()}
        with tempfile.TemporaryFile(mode="w+") as logs:
            process = subprocess.Popen([
                sys.executable, "-m", "uvicorn", "hospital.main:create_app", "--factory", "--app-dir", "backend/src",
                "--host", "127.0.0.1", "--port", str(port), "--no-access-log",
            ], cwd=ROOT, env=env, stdout=logs, stderr=logs)
            try:
                with httpx.Client(base_url=f"http://127.0.0.1:{port}", trust_env=False, timeout=5) as client:
                    await_live(client, process)
                    assert client.get("/api/v1/health/ready").status_code == 200
                    results = {}
                    for actor in (None, "desconocido-demo", "inactivo-demo", *ROLE_PERMISSIONS):
                        response = client.get("/api/v1/identity/me", headers={"X-Dev-Actor": actor} if actor else {})
                        expected = 200 if enabled and actor in ROLE_PERMISSIONS else 401
                        assert response.status_code == expected
                        UUID(response.headers["X-Request-ID"])
                        if expected == 200:
                            assert set(response.json()["permissions"]) == ROLE_PERMISSIONS[actor]
                        else:
                            assert response.json()["error"]["code"] == "IDENTITY_REQUIRED"
                        results[actor or "absent"] = response.status_code
                    report["http"][f"{environment}_identity_{enabled}"] = results
            finally:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
            logs.seek(0)
            output = logs.read()
            for secret in (configuration.database_url, configuration.test_database_url):
                if secret is not None:
                    assert make_url(secret.get_secret_value()).password not in output
            assert "Traceback" not in output

    # Fábrica real: producción con bandera activa falla antes de abrir PostgreSQL.
    invalid = subprocess.run([
        sys.executable, "-c", "from hospital.main import create_app; create_app()",
    ], cwd=ROOT, env={**os.environ, "PYTHONPATH": str(ROOT / "backend/src"),
                     "APP_ENV": "production", "DEV_IDENTITY_ENABLED": "true"}, capture_output=True, text=True)
    assert invalid.returncode != 0
    assert "ConfigurationError" in invalid.stderr
    for secret in (configuration.database_url, configuration.test_database_url):
        if secret is not None:
            assert make_url(secret.get_secret_value()).password not in invalid.stderr
    report["production_simulated_startup_rejected"] = True
    report["api_logs_credentials_exposed"] = False
    report["temporary_api_processes_stopped"] = True
    report["default_identity_enabled"] = configuration.dev_identity_enabled
    result = ROOT / "docs/evidencia/v1-03-resultados.json"
    result.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print("V1-03 verificada: semilla, permisos, proyecciones y aislamiento local.")
    print("Evidencia sin credenciales: docs/evidencia/v1-03-resultados.json")


if __name__ == "__main__":
    main()
