from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    DATABASE_URL: str = "postgresql+psycopg_async://archai:archai@localhost:5432/archai"
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:8080"
    ENV: str = "development"
    LOG_LEVEL: str = "INFO"
    SQL_ECHO: bool = False

    # Firebase Admin: full service account JSON string (preferred on Cloud Run / CI).
    # Use a single line or standard .env quoting; private_key newlines as \n in JSON.
    FIREBASE_CREDENTIALS_JSON: Optional[str] = None
    # Path to Firebase service account JSON file (local dev). Ignored if FIREBASE_CREDENTIALS_JSON is set.
    FIREBASE_CREDENTIALS_PATH: Optional[str] = None
    # Whether to check token revocation (extra Firebase RTDB call per verify).
    FIREBASE_CHECK_REVOKED: bool = False

    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""
    RAZORPAY_WEBHOOK_SECRET: str = ""
    RAZORPAY_CURRENCY: str = "INR"
    RAZORPAY_PRO_AMOUNT_PAISE: int = 99900
    RAZORPAY_LIFETIME_AMOUNT_PAISE: int = 499900
    RAZORPAY_PRO_VALIDITY_DAYS: int = 365

    @property
    def database_url(self) -> str:
        return self.DATABASE_URL

    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def razorpay_orders_configured(self) -> bool:
        return bool(self.RAZORPAY_KEY_ID.strip() and self.RAZORPAY_KEY_SECRET.strip())

    @property
    def razorpay_webhook_configured(self) -> bool:
        return bool(self.RAZORPAY_WEBHOOK_SECRET.strip())

    # Graph evaluation LLM (openai | stub)
    EVALUATION_LLM_PROVIDER: str = "stub"
    OPENAI_API_KEY: str = ""
    OPENAI_EVAL_MODEL: str = "gpt-4o-mini"
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    OPENAI_EVAL_TIMEOUT_S: float = 120.0

    # Interview mode: max user/assistant messages sent to the model (tail window)
    INTERVIEW_MAX_MESSAGES: int = 40

    # Free plan: max AI-backed calls per UTC calendar month (evaluate, interview turns, simulate)
    FREE_AI_CALLS_MONTHLY_LIMIT: int = 20


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
