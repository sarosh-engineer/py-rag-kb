"""Settings loading and validation."""

import pytest
from pydantic import ValidationError

from app.__main__ import server_options
from app.config import Settings


def test_declared_defaults_are_local_and_closed() -> None:
    defaults = {name: field.default for name, field in Settings.model_fields.items()}

    assert defaults == {
        "app_name": "genai-rag-assistant",
        "app_env": "local",
        "app_version": "0.1.0",
        "log_level": "INFO",
        "log_json": True,
        "host": "127.0.0.1",
        "port": 8000,
        "cors_allowed_origins": "",
        "jwt_secret_key": "",
        "jwt_algorithm": "HS256",
        "access_token_expire_minutes": 30,
        "bootstrap_admin_email": "",
        "bootstrap_admin_password": "",
        "mongodb_uri": "",
        "mongodb_database": "genai_rag",
        "aws_region": "",
        "aws_access_key_id": "",
        "aws_secret_access_key": "",
        "s3_bucket_name": "",
        "max_upload_bytes": 10 * 1024 * 1024,
    }


def test_environment_variables_override_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_NAME", "from-env")
    monkeypatch.setenv("APP_ENV", "Production")
    monkeypatch.setenv("LOG_LEVEL", "debug")
    monkeypatch.setenv("LOG_JSON", "false")
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "https://app.example.com/")

    settings = Settings()

    assert settings.app_name == "from-env"
    assert settings.app_env == "production"
    assert settings.log_level == "DEBUG"
    assert settings.log_json is False
    assert settings.is_production is True
    assert settings.cors_origins == ["https://app.example.com"]


def test_constructor_arguments_override_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")

    settings = Settings(app_env="test")

    assert settings.app_env == "test"


def test_wildcard_cors_origin_is_rejected() -> None:
    with pytest.raises(ValidationError, match="Wildcard CORS origin"):
        Settings(cors_allowed_origins="*")


def test_cors_origin_must_not_include_a_path() -> None:
    with pytest.raises(ValidationError, match="scheme, host, and optional port"):
        Settings(cors_allowed_origins="http://localhost:4200/app")


def test_local_server_binds_the_configured_address() -> None:
    settings = Settings(host="127.0.0.1", port=8000)

    assert server_options(settings) == {
        "app": "app.main:app",
        "host": "127.0.0.1",
        "port": 8000,
        "access_log": False,
    }


def test_port_must_be_in_range() -> None:
    with pytest.raises(ValidationError):
        Settings(port=0)
