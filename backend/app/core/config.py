"""App settings loaded from environment / .env (never hardcode secrets)."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=("../.env", ".env"), extra="ignore")

    app_name: str = "Attention Platform API"
    api_prefix: str = "/api/v1"

    database_url: str
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    access_expire_min: int = 15
    refresh_expire_days: int = 7


settings = Settings()  # type: ignore[call-arg]
