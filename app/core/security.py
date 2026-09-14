"""
app/core/security.py
────────────────────
All cryptographic operations live here.

  • Password hashing   — Argon2id (memory: 64MB, time: 3, parallelism: 4)
  • JWT               — RS256 asymmetric signing (private key signs, public key verifies)
  • Refresh tokens    — 64-byte cryptographically random opaque strings
  • Token revocation  — jti blocklist in Redis (TTL = remaining token lifetime)
  • TOTP              — RFC 6238 for admin 2FA

Security rules:
  • JWT private key NEVER leaves the backend.
  • Access tokens stored in JS memory only (not localStorage, not cookie).
  • Refresh tokens stored as httpOnly Secure SameSite=Strict cookie.
  • Refresh tokens are hashed (SHA-256) before storage in the DB.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHashError
from jose import JWTError, jwt
import pyotp

from app.core.config import settings
from app.core.exceptions import (
    TokenExpiredError,
    TokenInvalidError,
    TwoFactorInvalidError,
)
from app.core.logging import get_logger

logger = get_logger(__name__)

# ── Argon2id configuration ────────────────────────────────────────────────────
# Parameters from OWASP recommendations for interactive login
_hasher = PasswordHasher(
    time_cost=3,           # Iterations
    memory_cost=65536,     # 64 MB
    parallelism=4,
    hash_len=32,
    salt_len=16,
)


# ── Password hashing ──────────────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    """
    Hash a password with Argon2id.
    Returns an encoded hash string including salt and parameters.
    """
    return _hasher.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """
    Verify a plain password against an Argon2id hash.
    Returns False if the password is wrong — never raises.
    """
    try:
        return _hasher.verify(hashed, plain)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def password_needs_rehash(hashed: str) -> bool:
    """
    Returns True if the hash was created with outdated parameters.
    Call this on successful login and rehash if needed.
    """
    return _hasher.check_needs_rehash(hashed)


# ── JWT — RS256 ───────────────────────────────────────────────────────────────

def _load_private_key() -> str:
    key = settings.JWT_PRIVATE_KEY
    # Support newline-escaped keys from environment variables
    return key.replace("\\n", "\n")


def _load_public_key() -> str:
    key = settings.JWT_PUBLIC_KEY
    return key.replace("\\n", "\n")


def create_access_token(
    subject: str,
    role: str,
    extra_claims: dict[str, Any] | None = None,
) -> tuple[str, str]:
    """
    Create a signed RS256 access token.

    Returns:
        (encoded_token, jti) — jti is used for revocation.
    """
    now = datetime.now(UTC)
    expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    jti = secrets.token_hex(16)

    claims: dict[str, Any] = {
        "sub":  subject,          # user UUID
        "role": role,
        "iat":  now,
        "exp":  expire,
        "jti":  jti,
        "iss":  "drip-api",
        "aud":  "drip-client",
    }
    if extra_claims:
        claims.update(extra_claims)

    token = jwt.encode(
        claims,
        _load_private_key(),
        algorithm=settings.JWT_ALGORITHM,
    )
    return token, jti


def decode_access_token(token: str) -> dict[str, Any]:
    """
    Decode and verify a JWT access token.
    Raises TokenExpiredError or TokenInvalidError on failure.
    """
    try:
        payload = jwt.decode(
            token,
            _load_public_key(),
            algorithms=[settings.JWT_ALGORITHM],
            audience="drip-client",
            issuer="drip-api",
            options={"verify_exp": True},
        )
        return payload
    except JWTError as exc:
        msg = str(exc).lower()
        if "expired" in msg or "exp" in msg:
            raise TokenExpiredError() from exc
        raise TokenInvalidError(detail=str(exc)) from exc


async def is_token_revoked(jti: str) -> bool:
    """Check if a token's jti is on the Redis blocklist."""
    from app.core.redis import get_redis, RedisKeys
    try:
        result = await get_redis().get(RedisKeys.jwt_blocklist(jti))
        return result is not None
    except Exception:
        # Redis unavailable: assume not revoked (fail-open)
        logger.warning("security.revocation_check_failed", jti=jti[:8])
        return False


async def revoke_token(jti: str, expires_at: datetime) -> None:
    """Add a jti to the Redis blocklist. TTL = remaining token lifetime."""
    from app.core.redis import get_redis, RedisKeys
    try:
        now = datetime.now(UTC)
        remaining = max(1, int((expires_at - now).total_seconds()))
        await get_redis().setex(RedisKeys.jwt_blocklist(jti), remaining, "1")
    except Exception as exc:
        logger.error("security.revocation_failed", jti=jti[:8], error=str(exc))


# ── Refresh tokens ────────────────────────────────────────────────────────────

def generate_refresh_token() -> str:
    """Generate a 64-byte URL-safe opaque refresh token."""
    return secrets.token_urlsafe(64)


def hash_refresh_token(token: str) -> str:
    """SHA-256 hex digest of the token. Only the hash is stored in the DB."""
    return hashlib.sha256(token.encode()).hexdigest()


# ── Short-lived tokens (email verification, password reset) ───────────────────

def create_email_verify_token(user_id: str) -> str:
    """
    Create a short-lived (24h) JWT for email verification links.
    Signed with the same RS256 key.
    """
    now = datetime.now(UTC)
    token, _ = create_access_token(
        subject=user_id,
        role="verify_email",
        extra_claims={
            "exp": now + timedelta(hours=24),
            "aud": "drip-email-verify",
        },
    )
    return token


def decode_email_verify_token(token: str) -> str:
    """Decode email verify token and return user_id. Raises on invalid."""
    try:
        payload = jwt.decode(
            token,
            _load_public_key(),
            algorithms=[settings.JWT_ALGORITHM],
            audience="drip-email-verify",
        )
        return payload["sub"]
    except JWTError as exc:
        raise TokenInvalidError(detail=str(exc)) from exc


def create_password_reset_token(user_id: str) -> str:
    """Create a short-lived (1h) password reset token."""
    now = datetime.now(UTC)
    token, _ = create_access_token(
        subject=user_id,
        role="reset_password",
        extra_claims={
            "exp": now + timedelta(hours=1),
            "aud": "drip-pwd-reset",
        },
    )
    return token


def decode_password_reset_token(token: str) -> str:
    """Decode password reset token and return user_id. Raises on invalid."""
    try:
        payload = jwt.decode(
            token,
            _load_public_key(),
            algorithms=[settings.JWT_ALGORITHM],
            audience="drip-pwd-reset",
        )
        return payload["sub"]
    except JWTError as exc:
        raise TokenInvalidError(detail=str(exc)) from exc


# ── TOTP (Admin 2FA) ─────────────────────────────────────────────────────────

def generate_totp_secret() -> str:
    """Generate a new base32 TOTP secret."""
    return pyotp.random_base32()


def get_totp_uri(secret: str, email: str) -> str:
    """Return the otpauth:// URI for QR code generation."""
    return pyotp.totp.TOTP(secret).provisioning_uri(
        name=email,
        issuer_name="DRIP Marketplace",
    )


def verify_totp(secret: str, code: str) -> bool:
    """
    Verify a 6-digit TOTP code.
    Allows 1 step of drift (±30 seconds) for clock skew.
    """
    totp = pyotp.TOTP(secret)
    valid = totp.verify(code, valid_window=1)
    if not valid:
        raise TwoFactorInvalidError()
    return True


# ── Cookie helpers ─────────────────────────────────────────────────────────────

REFRESH_TOKEN_COOKIE_NAME = "drip_refresh_token"


def get_cookie_params() -> dict[str, Any]:
    """Return secure cookie parameters for the refresh token."""
    is_prod = settings.is_production
    return {
        "key":       REFRESH_TOKEN_COOKIE_NAME,
        "httponly":  True,
        "secure":    is_prod,         # HTTPS only in production
        "samesite":  "strict",
        "path":      "/api/v1/auth",  # Scoped to auth endpoints only
        "max_age":   settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
    }