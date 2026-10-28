from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_env: str = "development"
    database_url: str = "sqlite:///./telemedicine.db"
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret: str = "development-only-change-me-please"
    jwt_expire_minutes: int = 30
    rate_limit_per_minute: int = 120
    cors_origins: str = "http://localhost:3000"
    log_level: str = "INFO"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

@lru_cache
def get_settings() -> Settings:
    return Settings()
