from pydantic_settings import BaseSettings
from typing import Optional
from pydantic import Field

class Settings(BaseSettings):
    APP_VERSION: str = "local"
    CORS_ORIGIN: str = ""  # comma-separated
    DATABASE_URL: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None

    # Company
    COMPANY_NAME: str = "AA Alive Sdn Bhd"
    COMPANY_PHONE: str = "+6011 2868 6592"
    COMPANY_EMAIL: str = "contact@evin2u.com"
    COMPANY_ADDRESS: str = "10 Jalan Perusahaan Amari, Batu Caves, Kuala Lumpur"
    COMPANY_BANK: str = "CIMB Bank 8011366127"
    TAX_LABEL: str = "SST"
    TAX_PERCENT: float = 0.0

    # Worker
    WORKER_BATCH_SIZE: int = 10
    WORKER_POLL_SECS: float = 1.0
    WORKER_MAX_ATTEMPTS: int = 5

    # Auth
    JWT_SECRET: str = Field(env="JWT_SECRET")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    COOKIE_SECURE: bool = True

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()

def cors_origins_list() -> list[str]:
    raw = settings.CORS_ORIGIN or ""
    return [o.strip() for o in raw.split(",") if o.strip()]
