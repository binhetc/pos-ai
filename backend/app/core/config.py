from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "POS AI"
    DATABASE_URL: str = "postgresql+asyncpg://pos_ai:password@localhost:5432/pos_ai"
    REDIS_URL: str = "redis://localhost:6379/0"
    SECRET_KEY: str = "change-me-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480  # 8 hours (1 shift)
    ALGORITHM: str = "HS256"

    # VNPay gateway
    VNPAY_TMN_CODE: str = ""
    VNPAY_HASH_SECRET: str = ""
    VNPAY_PAYMENT_URL: str = "https://sandbox.vnpayment.vn/paymentv2/vpcpay.html"

    # MoMo gateway
    MOMO_PARTNER_CODE: str = ""
    MOMO_ACCESS_KEY: str = ""
    MOMO_SECRET_KEY: str = ""
    MOMO_ENDPOINT: str = "https://test-payment.momo.vn/v2/gateway/api/create"

    class Config:
        env_file = ".env"


settings = Settings()
