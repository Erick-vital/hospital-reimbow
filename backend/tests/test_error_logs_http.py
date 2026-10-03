"""Comprueba el log del servidor real, no sólo el logger de la aplicación."""
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
from uuid import UUID

import httpx
import pytest

pytestmark = pytest.mark.integration
ROOT = Path(__file__).resolve().parents[2]


def test_unexpected_exception_is_sanitized_in_uvicorn_logs(tmp_path):
    # Módulo exclusivo del test; no añade esta ruta a la aplicación del proyecto.
    module = tmp_path / "probe_app.py"
    module.write_text('''from hospital.main import create_app
app = create_app()
@app.get("/failure")
def fail():
    raise RuntimeError("PERSONAL_FICTICIO TOKEN_FICTICIO SQL_FICTICIO")
''')
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    logs_path = tmp_path / "uvicorn.log"
    with logs_path.open("w+") as logs:
        process = subprocess.Popen([
            sys.executable, "-m", "uvicorn", "probe_app:app", "--app-dir", str(tmp_path),
            "--host", "127.0.0.1", "--port", str(port), "--no-access-log",
        ], cwd=ROOT, env={**os.environ, "APP_ENV": "test", "DEV_IDENTITY_ENABLED": "false",
                          "PYTHONPATH": str(ROOT / "backend/src")}, stdout=logs, stderr=logs)
        try:
            with httpx.Client(base_url=f"http://127.0.0.1:{port}", trust_env=False, timeout=5) as client:
                for _ in range(100):
                    assert process.poll() is None, "API temporal no arrancó"
                    try:
                        if client.get("/api/v1/health/live").status_code == 200:
                            break
                    except httpx.TransportError:
                        pass
                    time.sleep(0.1)
                else:
                    pytest.fail("API temporal no disponible")
                response = client.get("/failure", headers={"X-Request-ID": "UNTRUSTED"})
                assert response.status_code == 500
                assert response.json()["error"]["code"] == "INTERNAL_ERROR"
                correlation = response.headers["X-Request-ID"]
                UUID(correlation)
                assert response.json()["request_id"] == correlation
                assert client.get("/api/v1/health/live").status_code == 200
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        logs.seek(0)
        output = logs.read()
    assert f"INTERNAL_ERROR request_id={correlation}" in output
    for marker in ("PERSONAL_FICTICIO", "TOKEN_FICTICIO", "SQL_FICTICIO", "Traceback", "RuntimeError"):
        assert marker not in output + response.text
