import secrets

from pydantic_settings import BaseSettings


def _generate_secret() -> str:
    """Generate a random secret key if none is provided via env."""
    return secrets.token_urlsafe(64)


class Settings(BaseSettings):
    PROJECT_NAME: str = "POS AI"
    DATABASE_URL: str = "postgresql+asyncpg://pos_ai:password@localhost:5432/pos_ai"
    REDIS_URL: str = "redis://localhost:6379/0"
    SECRET_KEY: str = _generate_secret()  # MUST be set via .env in production
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480  # 8 hours (1 shift)
    ALGORITHM: str = "HS256"
    MAX_UPLOAD_SIZE_MB: int = 5

    class Config:
        env_file = ".env"


settings = Settings()
