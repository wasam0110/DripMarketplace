"""
app/core/config.py
──────────────────
Single source of truth for all runtime configuration.
Every value comes from environment variables — never from code.
Validated at startup: missing required vars crash immediately with a clear message.
"""

from functools import lru_cache
from typing import Literal

from pydantic import field_validator, model_validator, PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",  # Silently ignore unknown vars
    )

    # ── App ───────────────────────────────────────────────────────────────────
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"
    APP_NAME: str = "DRIP API"
    APP_VERSION: str = "1.0.0"
    API_PREFIX: str = "/api/v1"
    DEBUG: bool = False

    # ── CORS ──────────────────────────────────────────────────────────────────
    ALLOWED_ORIGINS: list[str] = ["http://localhost:5173"]

    # ── Database ──────────────────────────────────────────────────────────────
    DATABASE_URL: str  # postgresql+asyncpg://user:pass@host:5432/db
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    DATABASE_POOL_TIMEOUT: int = 30

    # ── Redis ─────────────────────────────────────────────────────────────────
    REDIS_URL: str  # redis://user:pass@host:6379/0

    # ── Auth — JWT (RS256) ────────────────────────────────────────────────────
    JWT_PRIVATE_KEY: str          # PEM-encoded RS256 private key
    JWT_PUBLIC_KEY: str           # PEM-encoded RS256 public key
    JWT_ALGORITHM: str = "RS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # ── Supabase ──────────────────────────────────────────────────────────────
    SUPABASE_URL: str
    SUPABASE_SERVICE_ROLE_KEY: str   # NEVER expose to frontend
    SUPABASE_STORAGE_BUCKET_PRODUCTS: str = "products"
    SUPABASE_STORAGE_BUCKET_BRANDS: str = "brands"
    SUPABASE_STORAGE_BUCKET_INVOICES: str = "invoices"

    # ── Payments — JazzCash ───────────────────────────────────────────────────
    JAZZCASH_MERCHANT_ID: str = ""
    JAZZCASH_PASSWORD: str = ""
    JAZZCASH_INTEGRITY_SALT: str = ""
    JAZZCASH_RETURN_URL: str = ""
    JAZZCASH_BASE_URL: str = "https://sandbox.jazzcash.com.pk/CustomerPortal/transactionmanagement/merchantform"

    # ── Payments — Easypaisa ──────────────────────────────────────────────────
    EASYPAISA_STORE_ID: str = ""
    EASYPAISA_HASH_KEY: str = ""
    EASYPAISA_BASE_URL: str = "https://easypaystg.easypaisa.com.pk"

    # ── Payments — Stripe ─────────────────────────────────────────────────────
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_CURRENCY: str = "pkr"

    # ── Email — Resend ────────────────────────────────────────────────────────
    RESEND_API_KEY: str = ""
    FROM_EMAIL: str = "orders@drip.pk"
    FROM_NAME: str = "DRIP Marketplace"

    # ── WhatsApp ──────────────────────────────────────────────────────────────
    DRIP_WHATSAPP_NUMBER: str = "923000000000"

    # ── Business rules (override via system_settings table at runtime) ────────
    COMMISSION_RATE: float = 0.15
    REGISTRATION_FEE: int = 5000
    BASE_SLOTS: int = 50
    EXTRA_SLOT_PRICE: int = 50
    FREE_SHIPPING_THRESHOLD: int = 5000
    STANDARD_SHIPPING_FEE: int = 200
    COD_TIMEOUT_MINUTES: int = 30
    WALLET_HOLD_DAYS: int = 3
    MIN_WITHDRAWAL_AMOUNT: int = 500
    MAX_WITHDRAWAL_AMOUNT: int = 200_000
    MAX_COD_ORDER_AMOUNT: int = 25_000

    # ── Monitoring ────────────────────────────────────────────────────────────
    SENTRY_DSN: str = ""

    # ── Validators ────────────────────────────────────────────────────────────
    @field_validator("DATABASE_URL")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        if not v.startswith("postgresql+asyncpg://"):
            raise ValueError(
                "DATABASE_URL must use the 'postgresql+asyncpg://' scheme. "
                "Example: postgresql+asyncpg://user:pass@host:5432/drip"
            )
        return v

    @field_validator("COMMISSION_RATE")
    @classmethod
    def validate_commission_rate(cls, v: float) -> float:
        if not 0 < v < 1:
            raise ValueError("COMMISSION_RATE must be between 0 and 1 (e.g. 0.15 for 15%)")
        return v

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_origins(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            return [o.strip() for o in v.split(",") if o.strip()]
        return v

    @model_validator(mode="after")
    def validate_production_secrets(self) -> "Settings":
        """In production, critical secrets must be set."""
        if self.ENVIRONMENT == "production":
            required = [
                "JWT_PRIVATE_KEY", "JWT_PUBLIC_KEY",
                "SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY",
                "RESEND_API_KEY",
            ]
            missing = [k for k in required if not getattr(self, k, "")]
            if missing:
                raise ValueError(
                    f"Production environment is missing required secrets: {missing}"
                )
        return self

    # ── Derived properties ────────────────────────────────────────────────────
    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT == "development"

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @property
    def docs_url(self) -> str | None:
        """Disable OpenAPI docs in production."""
        return "/docs" if self.is_development else None

    @property
    def redoc_url(self) -> str | None:
        return "/redoc" if self.is_development else None


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


# Module-level singleton — import this everywhere
settings: Settings = get_settings()