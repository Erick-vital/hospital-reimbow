import pytest
from pydantic import ValidationError

from hospital.core.config import ConfigurationError, Settings, load_settings

DEV = "postgresql+psycopg://hospital_dev:FAKE_PASSWORD@127.0.0.1:5432/hospital_dev"
TEST = "postgresql+psycopg://hospital_test:FAKE_TEST_PASSWORD@127.0.0.1:5432/hospital_test"


def settings(**changes):
    return Settings(_env_file=None, database_url=DEV, test_database_url=TEST, **changes)


def test_default_identity_disabled_and_secret_hidden():
    configuration = settings()
    assert not configuration.dev_identity_enabled
    assert "FAKE_PASSWORD" not in repr(configuration)


def test_test_environment_selects_independent_database():
    assert settings(app_env="test").connection_url == TEST


def test_production_rejects_simulated_identity():
    with pytest.raises(ValidationError):
        settings(app_env="production", dev_identity_enabled=True)


@pytest.mark.parametrize("url", [
    "sqlite:///hospital.db",
    "postgresql://hospital_dev:FAKE@127.0.0.1/hospital_dev",
    "postgresql+psycopg://hospital_dev:FAKE@example.invalid/hospital_dev",
    "postgresql+psycopg://hospital_dev:FAKE@127.0.0.1/hospital_test",
    "postgresql+psycopg://hospital_dev@127.0.0.1/hospital_dev",
    DEV + "?host=example.invalid",
])
def test_invalid_development_database_rejected(url):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, app_env="development", database_url=url)


@pytest.mark.parametrize("url", [None, DEV, TEST.replace("//hospital_test:", "//hospital_dev:"), TEST.replace("/hospital_test", "/hospital_dev")])
def test_unsafe_test_database_rejected(url):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, app_env="test", database_url=DEV, test_database_url=url)


def test_startup_configuration_errors_do_not_expose_input(monkeypatch):
    secret = "SECRET_FOR_REDACTION_TEST"
    monkeypatch.setenv("DATABASE_URL", secret)
    with pytest.raises(ConfigurationError) as captured:
        load_settings()
    assert secret not in str(captured.value)
