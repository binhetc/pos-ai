from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "POS AI"
    DATABASE_URL: str = "postgresql+asyncpg://pos_ai:password@localhost:5432/pos_ai"
    REDIS_URL: str = "redis://localhost:6379/0"
    SECRET_KEY: str = "change-me-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480  # 8 hours (1 shift)
    ALGORITHM: str = "HS256"

    class Config:
        env_file = ".env"


settings = Settings()
