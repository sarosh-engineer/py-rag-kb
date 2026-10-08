"""Environment-based application settings.

The process environment is the source of truth. A repository-root ``.env``
file is loaded for local development when it exists. Secrets must never be
committed; ``.env.example`` documents names only.
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_REPO_ROOT = Path(__file__).resolve().parents[2]

EnvironmentName = Literal["local", "test", "development", "staging", "production"]
LogLevelName = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


def split_origins(value: str) -> list[str]:
    """Split a comma-separated origin list, dropping empty items."""
    return [item.strip() for item in value.split(",") if item.strip()]


class Settings(BaseSettings):
    """Runtime settings for one API process.

    Constructor arguments override environment variables. That lets tests
    build an isolated configuration without changing the process environment.
    """

    model_config = SettingsConfigDict(
        env_file=_REPO_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "genai-rag-assistant"
    app_env: EnvironmentName = "local"
    app_version: str = "0.1.0"
    log_level: LogLevelName = "INFO"
    log_json: bool = True
    host: str = "127.0.0.1"
    port: int = Field(default=8000, ge=1, le=65535)
    cors_allowed_origins: str = ""
    jwt_secret_key: str = ""
    jwt_algorithm: Literal["HS256", "HS384", "HS512"] = "HS256"
    access_token_expire_minutes: int = Field(default=30, ge=5, le=1440)
    bootstrap_admin_email: str = ""
    bootstrap_admin_password: str = ""

    @field_validator("app_env", mode="before")
    @classmethod
    def normalize_environment(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip().lower()
        return value

    @field_validator("log_level", mode="before")
    @classmethod
    def normalize_log_level(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip().upper()
        return value

    @field_validator("jwt_algorithm", mode="before")
    @classmethod
    def normalize_jwt_algorithm(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip().upper()
        return value

    @field_validator("jwt_secret_key", "bootstrap_admin_email", "bootstrap_admin_password")
    @classmethod
    def strip_secret_fields(cls, value: str) -> str:
        return value.strip()

    @field_validator("bootstrap_admin_email")
    @classmethod
    def normalize_bootstrap_email(cls, value: str) -> str:
        return value.lower()

    @field_validator("cors_allowed_origins")
    @classmethod
    def validate_cors_origins(cls, value: str) -> str:
        origins = split_origins(value)
        normalized: list[str] = []
        for origin in origins:
            if origin == "*":
                raise ValueError(
                    "Wildcard CORS origin '*' is not allowed. "
                    "List explicit origins in CORS_ALLOWED_ORIGINS."
                )
            parsed = urlparse(origin)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                raise ValueError(f"Invalid CORS origin: {origin}")
            if parsed.path not in {"", "/"} or parsed.params or parsed.query or parsed.fragment:
                raise ValueError(
                    f"CORS origin must be scheme, host, and optional port only: {origin}"
                )
            normalized.append(f"{parsed.scheme}://{parsed.netloc}")
        return ",".join(normalized)

    @property
    def cors_origins(self) -> list[str]:
        """Browser origins permitted to call this API."""
        return split_origins(self.cors_allowed_origins)

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def auth_is_configured(self) -> bool:
        """True when the signing key is long enough to use."""
        return len(self.jwt_secret_key) >= 32

    def validate_runtime(self) -> None:
        """Reject combinations that must not boot.

        Local and test processes may start without a JWT secret so ``/health``
        still works. Production may not. Bootstrap admin settings are all-or-nothing.
        """
        if self.is_production and not self.auth_is_configured:
            raise RuntimeError(
                "JWT_SECRET_KEY must be at least 32 characters when APP_ENV=production."
            )
        has_email = bool(self.bootstrap_admin_email)
        has_password = bool(self.bootstrap_admin_password)
        if has_email != has_password:
            raise RuntimeError(
                "Set both BOOTSTRAP_ADMIN_EMAIL and BOOTSTRAP_ADMIN_PASSWORD, or neither."
            )
        if has_password and not self.auth_is_configured:
            raise RuntimeError(
                "Bootstrap admin requires JWT_SECRET_KEY of at least 32 characters."
            )


@lru_cache
def load_settings() -> Settings:
    """Load process settings once.

    Tests that need a different configuration should pass a ``Settings``
    instance to ``create_app`` instead of clearing this cache.
    """
    return Settings()
