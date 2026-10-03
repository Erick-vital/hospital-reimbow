"""Genera credenciales de base locales sin imprimirlas ni reemplazar configuración."""
import os
from pathlib import Path
import secrets


def main() -> None:
    target = Path(__file__).resolve().parents[1] / ".env"
    admin, dev, test = (secrets.token_hex(24) for _ in range(3))
    content = (
        "APP_ENV=development\nDEV_IDENTITY_ENABLED=false\n"
        f"DATABASE_URL=postgresql+psycopg://hospital_dev:{dev}@127.0.0.1:5432/hospital_dev\n"
        f"TEST_DATABASE_URL=postgresql+psycopg://hospital_test:{test}@127.0.0.1:5432/hospital_test\n"
        f"POSTGRES_PASSWORD={admin}\nPG_DEV_PASSWORD={dev}\nPG_TEST_PASSWORD={test}\n"
    )
    try:
        fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        print("backend/.env ya existe; configuración conservada.")
        return
    with os.fdopen(fd, "w") as stream:
        stream.write(content)
    print("backend/.env creado con permisos 600; identidad simulada deshabilitada.")


if __name__ == "__main__":
    main()
