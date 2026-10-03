"""Ejecutar desde cualquier directorio; nunca imprime secretos."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sqlalchemy.exc import SQLAlchemyError

from hospital.core.config import ConfigurationError, load_settings
from hospital.core.database import Database
from hospital.identity.seed import SeedError, seed_local_identity


def main() -> int:
    database = None
    try:
        settings = load_settings()
        if settings.app_env == "production":
            raise SeedError("Semilla ficticia prohibida en producción")
        database = Database(settings)
        with database.sessions() as session:
            counts = seed_local_identity(session, settings)
        print("Semilla local comprobada: " + ", ".join(f"{key}={value}" for key, value in counts.items()))
        return 0
    except (ConfigurationError, SeedError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except SQLAlchemyError:
        print("No se pudo preparar la identidad local; revisar base y migraciones", file=sys.stderr)
        return 1
    finally:
        if database is not None:
            database.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
