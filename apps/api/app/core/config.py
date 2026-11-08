from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración de la aplicación leída desde variables de entorno / .env."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "CRM DATA SERVICE"
    environment: Literal["development", "test", "production"] = "development"
    api_prefix: str = "/api/v1"
    timezone: str = "America/Lima"

    database_url: str = "postgresql+psycopg://crm:crm@localhost:5432/crm"

    jwt_secret: SecretStr = SecretStr("change-me-in-env-file-please-32chars")
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 15
    refresh_token_days: int = 7
    refresh_cookie_name: str = "crm_refresh"
    cookie_secure: bool = False

    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])

    login_rate_limit: str = "5/minute"
    max_failed_logins: int = 5
    lockout_minutes: int = 15

    initial_admin_email: str = "admin@dataservice.pe"
    initial_admin_password: SecretStr = SecretStr("Admin123!")
    initial_admin_name: str = "Administrador del sistema"

    log_level: str = "INFO"

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
