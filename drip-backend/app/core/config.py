"""
app/core/config.py
──────────────────
Single source of truth for all runtime configuration.
Every value comes from environment variables — never from code.
Validated at startup: missing required vars crash immediately with a clear message.
"""

import os
from functools import lru_cache
from typing import Literal

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.public_urls import normalize_origin


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",  # Silently ignore unknown vars
    )

    # ── App ───────────────────────────────────────────────────────────────────
    ENVIRONMENT: Literal["development", "staging", "production", "test"] = "development"
    APP_NAME: str = "WearHowZ API"
    APP_VERSION: str = "1.0.0"
    # Auth cookie scopes and provider callbacks currently require this prefix.
    API_PREFIX: Literal["/api/v1"] = "/api/v1"
    DEBUG: bool = False

    # ── CORS ──────────────────────────────────────────────────────────────────
    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:5173"]
    # Only socket peers in these networks may supply forwarding headers.
    TRUSTED_PROXY_IPS: list[str] = []

    # ── Database ──────────────────────────────────────────────────────────────
    DATABASE_URL: str  # postgresql+asyncpg://user:pass@host:5432/db
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    DATABASE_POOL_TIMEOUT: int = 30

    # ── Redis ─────────────────────────────────────────────────────────────────
    REDIS_URL: str  # redis://user:pass@host:6379/0

    # ── Auth — JWT (RS256) ────────────────────────────────────────────────────
    JWT_PRIVATE_KEY: str  # PEM-encoded RS256 private key
    JWT_PUBLIC_KEY: str  # PEM-encoded RS256 public key
    JWT_ALGORITHM: Literal["RS256"] = "RS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # ── Supabase ──────────────────────────────────────────────────────────────
    SUPABASE_URL: str
    SUPABASE_SERVICE_ROLE_KEY: str  # NEVER expose to frontend
    SUPABASE_STORAGE_BUCKET_PRODUCTS: str = "products"
    SUPABASE_STORAGE_BUCKET_AVATARS: str = "avatars"
    SUPABASE_STORAGE_BUCKET_BRANDS: str = "brands"
    SUPABASE_STORAGE_BUCKET_INVOICES: str = "invoices"
    # Destructive maintenance stays opt-in even when storage credentials exist.
    SUPABASE_ORPHAN_CLEANUP_ENABLED: bool = False

    # ── Email — Resend ────────────────────────────────────────────────────────
    RESEND_API_KEY: str = ""
    FROM_EMAIL: str = "orders@example.com"
    FROM_NAME: str = "WearHowZ"

    # ── WhatsApp ──────────────────────────────────────────────────────────────
    DRIP_WHATSAPP_NUMBER: str = "923208306241"

    # ── Business defaults (only explicitly supported keys have DB overrides) ─
    COMMISSION_RATE: float = 0.15
    REGISTRATION_FEE: int = 5000
    BASE_SLOTS: int = 50
    EXTRA_SLOT_PRICE: int = 50
    FREE_SHIPPING_THRESHOLD: int = 5000
    STANDARD_SHIPPING_FEE: int = 200
    COD_TIMEOUT_MINUTES: int = 30
    PAYMENT_TIMEOUT_MINUTES: int = 30
    WALLET_HOLD_DAYS: int = 3
    # Startup-only PKR limits; restart API/workers together after changing them.
    MIN_WITHDRAWAL_AMOUNT: int = 500
    MAX_WITHDRAWAL_AMOUNT: int = 200_000
    MAX_COD_ORDER_AMOUNT: int = 25_000

    # ── Monitoring ────────────────────────────────────────────────────────────
    SENTRY_DSN: str = ""

    # ── Validators ────────────────────────────────────────────────────────────
    @model_validator(mode="after")
    def validate_withdrawal_limits(self) -> "Settings":
        """Keep configured payout limits within the database amount constraints."""
        # ck_payouts_amount_min fixes the database payout floor at PKR 500.
        # Wallet/payout NUMERIC(12, 2) allows ten whole-number digits.
        if not 500 <= self.MIN_WITHDRAWAL_AMOUNT <= self.MAX_WITHDRAWAL_AMOUNT <= 9_999_999_999:
            raise ValueError(
                "withdrawal limits must satisfy 500 <= MIN_WITHDRAWAL_AMOUNT "
                "<= MAX_WITHDRAWAL_AMOUNT <= 9999999999"
            )
        return self

    @field_validator("DATABASE_URL")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """Require the async PostgreSQL driver used by the session factory."""
        if not v.startswith("postgresql+asyncpg://"):
            raise ValueError(
                "DATABASE_URL must use the 'postgresql+asyncpg://' scheme. "
                "Example: postgresql+asyncpg://user:pass@host:5432/drip"
            )
        return v

    @field_validator("COMMISSION_RATE")
    @classmethod
    def validate_commission_rate(cls, v: float) -> float:
        """Reject commission fractions outside the exclusive zero-to-one range."""
        if not 0 < v < 1:
            raise ValueError("COMMISSION_RATE must be between 0 and 1 (e.g. 0.15 for 15%)")
        return v

    @field_validator(
        "ALLOWED_ORIGINS", "TRUSTED_PROXY_IPS", "PAYFAST_IPN_IPS",
        "PAYFAST_TRUSTED_PROXY_IPS", mode="before"
    )
    @classmethod
    def parse_origins(cls, v: str | list[str]) -> list[str]:
        """Accept comma-separated origins or proxy networks as configuration lists."""
        if isinstance(v, str):
            return [o.strip() for o in v.split(",") if o.strip()]
        return v

    @field_validator("FRONTEND_URL", "API_BASE_URL")
    @classmethod
    def validate_public_origin(cls, value: str) -> str:
        """Normalize the trusted origin used to construct public links."""
        return normalize_origin(value)

    @field_validator("ALLOWED_ORIGINS")
    @classmethod
    def validate_cors_origins(cls, values: list[str]) -> list[str]:
        """Normalize and deduplicate origins before CORS middleware consumes them."""
        return list(dict.fromkeys(normalize_origin(value) for value in values))

    @model_validator(mode="after")
    def validate_production_secrets(self) -> "Settings":
        """In production, critical secrets must be set."""
        if self.ENVIRONMENT == "production":
            required = [
                "JWT_PRIVATE_KEY",
                "JWT_PUBLIC_KEY",
                "SUPABASE_URL",
                "SUPABASE_SERVICE_ROLE_KEY",
                "RESEND_API_KEY",
            ]
            missing = [k for k in required if not getattr(self, k, "")]
            if missing:
                raise ValueError(f"Production environment is missing required secrets: {missing}")
            for name in ("FRONTEND_URL", "API_BASE_URL"):
                if not getattr(self, name).startswith("https://"):
                    raise ValueError(f"{name} must use HTTPS in production")
        if self.PAYFAST_ENABLED:
            payfast_required = [
                "PAYFAST_MERCHANT_ID",
                "PAYFAST_SECURED_KEY",
                "PAYFAST_MERCHANT_NAME",
                "PAYFAST_API_BASE_URL",
            ]
            missing = [key for key in payfast_required if not getattr(self, key, "").strip()]
            if missing:
                raise ValueError(f"Enabled PayFast is missing configuration: {missing}")
            if self.ENVIRONMENT == "production":
                if self.PAYFAST_SANDBOX:
                    raise ValueError("PAYFAST_SANDBOX must be false in production")
        if bool(self.GOOGLE_CLIENT_ID) != bool(self.GOOGLE_CLIENT_SECRET):
            raise ValueError("Google OAuth requires both GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET")
        if self.ENVIRONMENT == "production" and self.FROM_EMAIL.endswith("@example.com"):
            raise ValueError("FROM_EMAIL must use a verified production domain")
        return self

    # ── Payments — PayFast ───────────────────────────────────────────────────
    PAYFAST_MERCHANT_ID: str = ""
    PAYFAST_SECURED_KEY: str = ""
    PAYFAST_MERCHANT_NAME: str = "WearHowZ"
    PAYFAST_SANDBOX: bool = True
    # Leave endpoint overrides empty to use the documented Pakistan UAT/live hosted URLs.
    PAYFAST_TOKEN_URL: str = ""
    PAYFAST_CHECKOUT_URL: str = ""
    # PayFast supplies an API base URL separately when status-query access is enabled.
    PAYFAST_API_BASE_URL: str = ""
    PAYFAST_REQUEST_TIMEOUT_SECONDS: int = 15
    # Enable only after the merchant-specific protocol and sandbox flow are verified.
    PAYFAST_ENABLED: bool = False
    # Comma-separated list of PayFast IPN server IPs for allowlisting.
    # Empty list = accept from any IP (safe for sandbox / local dev).
    # Populate with PayFast Pakistan's published IPN IP ranges before go-live.
    # REQUIRES_LIVE_VERIFICATION: obtain IP list from PayFast Pakistan support.
    PAYFAST_IPN_IPS: list[str] = []
    # Forwarding headers are ignored unless the direct peer is in this list.
    PAYFAST_TRUSTED_PROXY_IPS: list[str] = []
    GUEST_ORDER_TOKEN_DAYS: int = 7
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""

    # ── App URLs ──────────────────────────────────────────────────────────────
    FRONTEND_URL: str = "http://localhost:3000"
    API_BASE_URL: str = "http://localhost:8000"

    # ── Derived properties ────────────────────────────────────────────────────
    @property
    def is_development(self) -> bool:
        """Expose the development-mode switch used by logging and API documentation."""
        return self.ENVIRONMENT == "development"

    @property
    def is_production(self) -> bool:
        """Expose the production-mode switch used by security configuration."""
        return self.ENVIRONMENT == "production"

    @property
    def docs_url(self) -> str | None:
        """Disable OpenAPI docs in production."""
        return "/docs" if self.is_development else None

    @property
    def redoc_url(self) -> str | None:
        """Enable the ReDoc route only in development."""
        return "/redoc" if self.is_development else None


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cache validated runtime settings; tests deliberately skip the local .env file."""
    # A test process must never inherit application secrets from the local .env.
    return Settings(_env_file=None if os.environ.get("ENVIRONMENT") == "test" else ".env")


# Module-level singleton — import this everywhere
settings: Settings = get_settings()
