import os
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    APP_NAME: str = "BinBot AI Trading"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/binbot"
    DATABASE_URL_SYNC: str = "postgresql://postgres:postgres@localhost:5432/binbot"
    REDIS_URL: str = "redis://localhost:6379/0"

    SECRET_KEY: str = os.getenv("SECRET_KEY", "change-me-in-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    BINANCE_API_URL: str = "https://fapi.binance.com"
    BINANCE_WS_URL: str = "wss://fstream.binance.com/ws"
    BINANCE_TESTNET_API_URL: str = "https://testnet.binancefuture.com"
    BINANCE_TESTNET_WS_URL: str = "wss://stream.binancefuture.com/ws"

    ENCRYPTION_KEY: str = os.getenv("ENCRYPTION_KEY", "change-me-32-chars-long-key!!")

    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_PRICE_FREE: str = ""
    STRIPE_PRICE_STARTER: str = ""
    STRIPE_PRICE_PRO: str = ""
    STRIPE_PRICE_ENTERPRISE: str = ""

    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "noreply@binbot.ai"

    FRONTEND_URL: str = "http://localhost:3000"
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:8000"]

    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET: str = "binbot-data"

    RATE_LIMIT_PER_MINUTE: int = 60

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()
