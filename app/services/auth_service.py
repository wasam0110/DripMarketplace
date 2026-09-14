"""
app/services/auth_service.py
─────────────────────────────
Authentication business logic.
Routes delegate here — no DB access in route handlers.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import (
    AuthenticationError,
    BusinessRuleError,
    ConflictError,
    DuplicateEmailError,
    EmailNotVerifiedError,
    InvalidCredentialsError,
    NotFoundError,
    TwoFactorRequiredError,
    TokenInvalidError,
)
from app.core.logging import get_logger
from app.core.security import (
    REFRESH_TOKEN_COOKIE_NAME,
    create_access_token,
    create_email_verify_token,
    create_password_reset_token,
    decode_email_verify_token,
    decode_password_reset_token,
    generate_refresh_token,
    generate_totp_secret,
    get_cookie_params,
    get_totp_uri,
    hash_password,
    hash_refresh_token,
    password_needs_rehash,
    revoke_token,
    verify_password,
    verify_totp,
)
from app.models.user import User, UserRole
from app.repositories.user_repo import SessionRepository, UserRepository
from app.schemas.auth import (
    AuthResponse,
    RegisterRequest,
    TOTPSetupResponse,
    TokenResponse,
    UserResponse,
)

logger = get_logger(__name__)


def _user_to_response(user: User, seller_id: str | None = None) -> UserResponse:
    return UserResponse(
        id=str(user.id),
        email=user.email,
        role=user.role.value,
        first_name=user.first_name,
        last_name=user.last_name,
        phone=user.phone,
        avatar_url=user.avatar_url,
        has_verified_email=user.has_verified_email,
        is_2fa_enabled=user.is_2fa_enabled,
        seller_id=seller_id,
        created_at=user.created_at,
    )


class AuthService:

    # ── Register ──────────────────────────────────────────────────────────────

    @staticmethod
    async def register(
        db: AsyncSession,
        payload: RegisterRequest,
    ) -> dict:
        """
        Create a new customer account.
        Returns the user + verification token (token sent via email by the route).
        """
        if await UserRepository.email_exists(db, payload.email):
            raise DuplicateEmailError()

        user = await UserRepository.create(
            db,
            email=payload.email,
            password_hash=hash_password(payload.password),
            first_name=payload.first_name,
            last_name=payload.last_name,
            phone=payload.phone,
            role=UserRole.customer,
            has_verified_email=False,
        )
        await db.commit()

        verify_token = create_email_verify_token(str(user.id))
        logger.info("auth.registered", user_id=str(user.id), email=user.email)
        return {"user": user, "verify_token": verify_token}

    # ── Email verification ────────────────────────────────────────────────────

    @staticmethod
    async def verify_email(db: AsyncSession, token: str) -> AuthResponse:
        """Verify email address via token link. Returns auth tokens on success."""
        try:
            user_id = decode_email_verify_token(token)
        except TokenInvalidError:
            raise BusinessRuleError(
                message="Verification link is invalid or has expired. Please request a new one.",
                code="INVALID_VERIFY_TOKEN",
            )

        user = await UserRepository.get_by_id_or_raise(db, user_id, resource="User")
        if user.has_verified_email:
            raise BusinessRuleError(message="Email address is already verified.", code="ALREADY_VERIFIED")

        await UserRepository.verify_email(db, user.id)
        await db.commit()
        await db.refresh(user)

        access_token, _ = create_access_token(subject=str(user.id), role=user.role.value)
        refresh_token    = generate_refresh_token()
        await SessionRepository.create(
            db,
            user_id=user.id,
            token_hash=hash_refresh_token(refresh_token),
            expires_at=datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        )
        await db.commit()

        logger.info("auth.email_verified", user_id=str(user.id))
        return AuthResponse(
            access_token=access_token,
            user=_user_to_response(user),
        ), refresh_token

    # ── Login ─────────────────────────────────────────────────────────────────

    @staticmethod
    async def login(
        db: AsyncSession,
        email: str,
        password: str,
        totp_code: str | None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> tuple[AuthResponse, str]:
        """
        Authenticate with email + password (+ TOTP for admins).
        Returns (AuthResponse, raw_refresh_token).
        The refresh token must be set as a cookie by the route handler.
        """
        user = await UserRepository.get_by_email(db, email)
        if not user or not user.password_hash:
            # Constant-time: always hash even on miss to prevent timing attacks
            hash_password("dummy_constant_time_prevention")
            raise InvalidCredentialsError()

        if not verify_password(password, user.password_hash):
            raise InvalidCredentialsError()

        if not user.has_verified_email:
            raise EmailNotVerifiedError()

        # Admin accounts require TOTP
        if user.role == UserRole.admin and user.is_2fa_enabled:
            if not totp_code:
                raise TwoFactorRequiredError()
            verify_totp(user.totp_secret, totp_code)

        # Rehash if params are outdated (e.g. after Argon2 parameter upgrade)
        if password_needs_rehash(user.password_hash):
            await UserRepository.update_password(db, user.id, hash_password(password))

        await UserRepository.update_last_login(db, user.id)

        # Build tokens
        extra: dict = {}
        seller_id: str | None = None
        if user.role == UserRole.seller and user.seller:
            seller_id = str(user.seller.id)
            extra["seller_id"] = seller_id

        access_token, _ = create_access_token(
            subject=str(user.id),
            role=user.role.value,
            extra_claims=extra,
        )
        refresh_token = generate_refresh_token()
        await SessionRepository.create(
            db,
            user_id=user.id,
            token_hash=hash_refresh_token(refresh_token),
            expires_at=datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
            ip_address=ip_address,
            user_agent=user_agent,
        )
        await db.commit()

        logger.info("auth.login", user_id=str(user.id), role=user.role.value)
        return AuthResponse(
            access_token=access_token,
            user=_user_to_response(user, seller_id=seller_id),
        ), refresh_token

    # ── Refresh ───────────────────────────────────────────────────────────────

    @staticmethod
    async def refresh_token(
        db: AsyncSession,
        raw_refresh_token: str,
    ) -> tuple[TokenResponse, str]:
        """
        Validate refresh token → rotate → return new access + refresh tokens.
        Old token is deleted (rotation prevents replay attacks).
        """
        token_hash = hash_refresh_token(raw_refresh_token)
        session = await SessionRepository.get_by_token_hash(db, token_hash)

        if not session:
            raise AuthenticationError(
                message="Session not found or expired. Please log in again.",
                code="SESSION_EXPIRED",
            )

        user = await UserRepository.get_by_id_or_raise(db, session.user_id)

        # Rotate: delete old, create new
        await SessionRepository.delete_by_token_hash(db, token_hash)

        new_refresh = generate_refresh_token()
        await SessionRepository.create(
            db,
            user_id=user.id,
            token_hash=hash_refresh_token(new_refresh),
            expires_at=datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        )

        extra: dict = {}
        if user.role == UserRole.seller and user.seller:
            extra["seller_id"] = str(user.seller.id)

        access_token, _ = create_access_token(
            subject=str(user.id),
            role=user.role.value,
            extra_claims=extra,
        )
        await db.commit()

        logger.info("auth.token_refreshed", user_id=str(user.id))
        return TokenResponse(access_token=access_token), new_refresh

    # ── Logout ────────────────────────────────────────────────────────────────

    @staticmethod
    async def logout(
        db: AsyncSession,
        raw_refresh_token: str,
        access_jti: str,
        access_exp: datetime,
    ) -> None:
        """
        Invalidate refresh token session + blocklist the access token jti.
        """
        token_hash = hash_refresh_token(raw_refresh_token)
        await SessionRepository.delete_by_token_hash(db, token_hash)
        await db.commit()
        await revoke_token(access_jti, access_exp)
        logger.info("auth.logout", jti=access_jti[:8])

    # ── Forgot password ───────────────────────────────────────────────────────

    @staticmethod
    async def forgot_password(db: AsyncSession, email: str) -> str | None:
        """
        Generate a password reset token.
        Always returns 200 to prevent email enumeration.
        Returns token only if user exists (for task to send email).
        """
        user = await UserRepository.get_by_email(db, email)
        if not user or not user.has_verified_email:
            return None   # Silently ignore — don't reveal existence
        token = create_password_reset_token(str(user.id))
        logger.info("auth.password_reset_requested", user_id=str(user.id))
        return token

    # ── Reset password ────────────────────────────────────────────────────────

    @staticmethod
    async def reset_password(db: AsyncSession, token: str, new_password: str) -> None:
        try:
            user_id = decode_password_reset_token(token)
        except TokenInvalidError:
            raise BusinessRuleError(
                message="Password reset link is invalid or has expired.",
                code="INVALID_RESET_TOKEN",
            )

        user = await UserRepository.get_by_id_or_raise(db, user_id)
        new_hash = hash_password(new_password)
        await UserRepository.update_password(db, user.id, new_hash)

        # Invalidate all sessions (force re-login everywhere)
        await SessionRepository.delete_all_for_user(db, user.id)
        await db.commit()
        logger.info("auth.password_reset", user_id=str(user.id))

    # ── Change password ───────────────────────────────────────────────────────

    @staticmethod
    async def change_password(
        db: AsyncSession,
        user_id: uuid.UUID,
        current_password: str,
        new_password: str,
    ) -> None:
        user = await UserRepository.get_by_id_or_raise(db, user_id)
        if not user.password_hash or not verify_password(current_password, user.password_hash):
            raise InvalidCredentialsError(message="Current password is incorrect.")
        await UserRepository.update_password(db, user.id, hash_password(new_password))
        await SessionRepository.delete_all_for_user(db, user.id)
        await db.commit()
        logger.info("auth.password_changed", user_id=str(user_id))

    # ── TOTP setup (admin) ────────────────────────────────────────────────────

    @staticmethod
    async def setup_totp(db: AsyncSession, user_id: uuid.UUID) -> TOTPSetupResponse:
        user = await UserRepository.get_by_id_or_raise(db, user_id)
        secret = generate_totp_secret()
        qr_uri = get_totp_uri(secret, user.email)
        # Store secret but don't enable 2FA until verified
        await UserRepository.set_totp(db, user.id, secret=secret, enabled=False)
        await db.commit()
        return TOTPSetupResponse(secret=secret, qr_uri=qr_uri)

    @staticmethod
    async def verify_and_enable_totp(
        db: AsyncSession, user_id: uuid.UUID, code: str
    ) -> None:
        user = await UserRepository.get_by_id_or_raise(db, user_id)
        if not user.totp_secret:
            raise BusinessRuleError(
                message="Please call /auth/setup-2fa first to generate a secret.",
                code="TOTP_NOT_CONFIGURED",
            )
        verify_totp(user.totp_secret, code)
        await UserRepository.set_totp(db, user.id, secret=user.totp_secret, enabled=True)
        await db.commit()
        logger.info("auth.2fa_enabled", user_id=str(user_id))