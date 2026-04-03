from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Base
    APP_NAME: str = "Bras Droit API"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    FRONTEND_URL: str = "http://localhost:3000"

    # Base de données
    DATABASE_URL: str

    # JWT
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24h

    # IA Anthropic
    ANTHROPIC_API_KEY: Optional[str] = None

    # APIs externes
    JEDECLARE_API_KEY: Optional[str] = None
    NORDIGEN_SECRET_ID: Optional[str] = None
    NORDIGEN_SECRET_KEY: Optional[str] = None

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
