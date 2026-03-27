from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

class Settings(BaseSettings):
    DATABASE_URL: str
    JWT_SECRET: str
    NEXT_PUBLIC_APP_URL: str
    RESEND_API_KEY: str
    APP_MAIL: str
    PROJECT_NAME: str = "thebarberdotcom"
    API_V1_STR: str = "/api/v1"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

@lru_cache
def settings():
    return Settings()
