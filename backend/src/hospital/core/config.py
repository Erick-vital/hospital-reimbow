from pathlib import Path
from typing import Literal

from pydantic import SecretStr, ValidationError, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url

ENV_FILE = Path(__file__).resolve().parents[3] / ".env"


class ConfigurationError(RuntimeError):
    """Error público de configuración, sin valores sensibles."""


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILE, env_file_encoding="utf-8", extra="ignore"
    )

    app_env: Literal["development", "test", "production"] = "development"
    dev_identity_enabled: bool = False
    database_url: SecretStr
    test_database_url: SecretStr | None = None

    @model_validator(mode="after")
    def validate_environment(self) -> "Settings":
        if self.app_env == "production" and self.dev_identity_enabled:
            raise ValueError("Identidad simulada prohibida en producción")
        urls = [self.database_url]
        if self.test_database_url is not None:
            urls.append(self.test_database_url)
        for secret in urls:
            try:
                url = make_url(secret.get_secret_value())
            except Exception:
                raise ValueError("URL PostgreSQL inválida") from None
            if url.drivername != "postgresql+psycopg" or not url.database:
                raise ValueError("Se requiere PostgreSQL con Psycopg 3")
            if not url.username or not url.password or url.query:
                raise ValueError("URL requiere credenciales y no admite opciones externas")
            if self.app_env in {"development", "test"} and url.host not in {"127.0.0.1", "localhost", "::1"}:
                raise ValueError("Las bases locales requieren interfaz loopback")
        if self.app_env == "development" and make_url(self.database_url.get_secret_value()).database != "hospital_dev":
            raise ValueError("Desarrollo requiere hospital_dev")
        if self.test_database_url is not None:
            test = make_url(self.test_database_url.get_secret_value())
            dev = make_url(self.database_url.get_secret_value())
            if test.database != "hospital_test" or test.database == dev.database or test.username == dev.username:
                raise ValueError("Pruebas requieren hospital_test y usuario independiente")
        if self.app_env == "test" and self.test_database_url is None:
            raise ValueError("Pruebas requieren TEST_DATABASE_URL explícita")
        return self

    @property
    def connection_url(self) -> str:
        if self.app_env == "test":
            assert self.test_database_url is not None
            return self.test_database_url.get_secret_value()
        return self.database_url.get_secret_value()


def load_settings() -> Settings:
    try:
        return Settings()
    except ValidationError as exc:
        fields = sorted({".".join(map(str, e["loc"])) or "entorno" for e in exc.errors(include_input=False, include_context=False)})
        raise ConfigurationError("Configuración inválida: " + ", ".join(fields)) from None
