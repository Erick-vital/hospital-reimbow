"""Prepara el entorno local existente, sin instalar paquetes ni borrar datos."""
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend/src"))

from hospital.core.config import ConfigurationError, load_settings


def run(*arguments, env=None):
    subprocess.run(arguments, cwd=ROOT, env=env, check=True)


def main():
    # Rechazar producción antes de escribir configuración o iniciar servicios.
    if os.environ.get("APP_ENV", "development") not in {"development", "test"}:
        raise RuntimeError("Preparación permitida sólo en desarrollo/pruebas")
    run(sys.executable, "backend/scripts/configure_local.py")
    settings = load_settings()
    if settings.app_env not in {"development", "test"} or settings.dev_identity_enabled:
        raise RuntimeError("Preparación requiere entorno local e identidad apagada")
    run(sys.executable, "-m", "pip", "check")
    run("docker", "compose", "--env-file", "backend/.env", "up", "-d", "--wait", "postgres")
    for environment in ("development", "test"):
        env = {**os.environ, "APP_ENV": environment, "DEV_IDENTITY_ENABLED": "false"}
        run(sys.executable, "-m", "alembic", "-c", "backend/alembic.ini", "upgrade", "head", env=env)
        run(sys.executable, "-m", "alembic", "-c", "backend/alembic.ini", "check", env=env)
        run(sys.executable, "backend/scripts/seed_identity.py", env=env)
    print("Preparación local completa; configuración y datos conservados, identidad apagada.")


if __name__ == "__main__":
    try:
        main()
    except (ConfigurationError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from None
