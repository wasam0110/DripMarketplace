"""
app/api/v1/auth.py
───────────────────
Auth routes — thin handlers that delegate everything to AuthService.
Each route: validate input → call service → set cookie if needed → return response.
"""
from __future__ import annotations

from fastapi import APIRouter, Cookie, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, DBSession, get_current_user_payload
from app.core.security import REFRESH_TOKEN_COOKIE_NAME, get_cookie_params
from app.schemas.auth import (
    AuthResponse,
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    MessageResponse,
    RegisterRequest,
    ResetPasswordRequest,
    TOTPSetupResponse,
    TokenResponse,
    UserResponse,
    VerifyTOTPRequest,
)
from app.services.auth_service import AuthService

router = APIRouter()


# ── POST /auth/register ───────────────────────────────────────────────────────

@router.post(
    "/register",
    response_model=MessageResponse,
    status_code=201,
    summary="Register a new customer account",
)
async def register(
    payload: RegisterRequest,
    db: DBSession,
) -> MessageResponse:
    """
    Create a new customer account.
    Sends a verification email — account is not active until email is verified.
    Rate limited: 3 per hour per IP.
    """
    result = await AuthService.register(db, payload)
    user   = result["user"]
    token  = result["verify_token"]

    # Enqueue verification email (non-blocking)
    try:
        from arq import create_pool
        from arq.connections import RedisSettings
        from app.core.config import settings as cfg
        pool = await create_pool(RedisSettings.from_dsn(cfg.REDIS_URL))
        await pool.enqueue_job(
            "task_send_verification_email",
            user.email, user.first_name or "there", token,
        )
        await pool.aclose()
    except Exception:
        # Email task failure is non-fatal — user can request resend
        pass

    return MessageResponse(
        message="Account created. Please check your email to verify your account."
    )


# ── GET /auth/verify-email ────────────────────────────────────────────────────

@router.get(
    "/verify-email",
    response_model=AuthResponse,
    summary="Verify email via token link",
)
async def verify_email(
    token: str,
    response: Response,
    db: DBSession,
) -> AuthResponse:
    """
    Called when the user clicks the verification link in their email.
    Returns access token + sets refresh token cookie on success.
    """
    auth, refresh_token = await AuthService.verify_email(db, token)
    _set_refresh_cookie(response, refresh_token)
    return auth


# ── POST /auth/login ──────────────────────────────────────────────────────────

@router.post(
    "/login",
    response_model=AuthResponse,
    summary="Login with email and password",
)
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: DBSession,
) -> AuthResponse:
    """
    Authenticate and receive tokens.
    Admin accounts require a valid TOTP code in `totp_code`.
    Rate limited: 5 per 5 minutes per IP.
    Refresh token is returned as an httpOnly cookie.
    """
    ip = _get_ip(request)
    ua = request.headers.get("user-agent", "")[:500]

    auth, refresh_token = await AuthService.login(
        db=db,
        email=payload.email,
        password=payload.password,
        totp_code=payload.totp_code,
        ip_address=ip,
        user_agent=ua,
    )
    _set_refresh_cookie(response, refresh_token)
    return auth


# ── POST /auth/refresh ────────────────────────────────────────────────────────

@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Rotate refresh token and get new access token",
)
async def refresh(
    response: Response,
    db: DBSession,
    refresh_token: str | None = Cookie(default=None, alias=REFRESH_TOKEN_COOKIE_NAME),
) -> TokenResponse:
    """
    Exchange a valid refresh token (from httpOnly cookie) for a new access token.
    Old refresh token is deleted; a new one is issued (token rotation).
    """
    if not refresh_token:
        from app.core.exceptions import AuthenticationError
        raise AuthenticationError(message="No refresh token found. Please log in again.")

    token_resp, new_refresh = await AuthService.refresh_token(db, refresh_token)
    _set_refresh_cookie(response, new_refresh)
    return token_resp


# ── POST /auth/logout ─────────────────────────────────────────────────────────

@router.post(
    "/logout",
    status_code=204,
    summary="Invalidate current session",
)
async def logout(
    response: Response,
    db: DBSession,
    payload: dict = Depends(get_current_user_payload),
    refresh_token: str | None = Cookie(default=None, alias=REFRESH_TOKEN_COOKIE_NAME),
) -> None:
    """
    Revoke the refresh token + blocklist the current access token.
    Clears the refresh token cookie.
    """
    if refresh_token:
        from datetime import UTC, datetime, timedelta
        exp_ts = payload.get("exp", 0)
        exp_dt = datetime.fromtimestamp(exp_ts, tz=UTC)
        await AuthService.logout(
            db=db,
            raw_refresh_token=refresh_token,
            access_jti=payload.get("jti", ""),
            access_exp=exp_dt,
        )
    _clear_refresh_cookie(response)


# ── POST /auth/forgot-password ────────────────────────────────────────────────

@router.post(
    "/forgot-password",
    response_model=MessageResponse,
    summary="Request a password reset email",
)
async def forgot_password(
    payload: ForgotPasswordRequest,
    db: DBSession,
) -> MessageResponse:
    """
    Always returns 200 regardless of whether the email exists (prevents enumeration).
    Rate limited: 3 per hour per IP.
    """
    token = await AuthService.forgot_password(db, payload.email)
    if token:
        try:
            from arq import create_pool
            from arq.connections import RedisSettings
            from app.core.config import settings as cfg
            from app.repositories.user_repo import UserRepository
            user = await UserRepository.get_by_email(db, payload.email)
            pool = await create_pool(RedisSettings.from_dsn(cfg.REDIS_URL))
            await pool.enqueue_job(
                "task_send_password_reset_email",
                payload.email,
                user.first_name or "there",
                token,
            )
            await pool.aclose()
        except Exception:
            pass

    return MessageResponse(
        message="If an account exists for that email, a reset link has been sent."
    )


# ── POST /auth/reset-password ─────────────────────────────────────────────────

@router.post(
    "/reset-password",
    response_model=MessageResponse,
    summary="Reset password using the link from email",
)
async def reset_password(
    payload: ResetPasswordRequest,
    db: DBSession,
) -> MessageResponse:
    await AuthService.reset_password(db, payload.token, payload.new_password)
    return MessageResponse(
        message="Password updated successfully. Please log in with your new password."
    )


# ── GET /auth/me ──────────────────────────────────────────────────────────────

@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current authenticated user",
)
async def get_me(
    db: DBSession,
    token_payload: CurrentUser,
) -> UserResponse:
    """Return the profile of the currently authenticated user."""
    from app.repositories.user_repo import UserRepository
    user = await UserRepository.get_by_id_or_raise(db, token_payload["sub"])
    seller_id = token_payload.get("seller_id")
    from app.services.auth_service import _user_to_response
    return _user_to_response(user, seller_id=seller_id)


# ── POST /auth/change-password ────────────────────────────────────────────────

@router.post(
    "/change-password",
    response_model=MessageResponse,
    summary="Change password (authenticated)",
)
async def change_password(
    payload: ChangePasswordRequest,
    response: Response,
    db: DBSession,
    token_payload: CurrentUser,
) -> MessageResponse:
    import uuid
    await AuthService.change_password(
        db=db,
        user_id=uuid.UUID(token_payload["sub"]),
        current_password=payload.current_password,
        new_password=payload.new_password,
    )
    _clear_refresh_cookie(response)
    return MessageResponse(
        message="Password changed. All sessions have been signed out."
    )


# ── POST /auth/setup-2fa ──────────────────────────────────────────────────────

@router.post(
    "/setup-2fa",
    response_model=TOTPSetupResponse,
    summary="Initialise TOTP 2FA (admin accounts only)",
)
async def setup_2fa(
    db: DBSession,
    token_payload: CurrentUser,
) -> TOTPSetupResponse:
    """
    Generate a TOTP secret and QR code URI for the authenticator app.
    Admin must then verify with /auth/setup-2fa/verify before 2FA is active.
    """
    if token_payload.get("role") != "admin":
        from app.core.exceptions import PermissionDeniedError
        raise PermissionDeniedError(message="2FA setup is only available for admin accounts.")

    import uuid
    return await AuthService.setup_totp(db, uuid.UUID(token_payload["sub"]))


# ── POST /auth/setup-2fa/verify ───────────────────────────────────────────────

@router.post(
    "/setup-2fa/verify",
    response_model=MessageResponse,
    summary="Verify TOTP code and enable 2FA",
)
async def verify_2fa_setup(
    payload: VerifyTOTPRequest,
    db: DBSession,
    token_payload: CurrentUser,
) -> MessageResponse:
    import uuid
    await AuthService.verify_and_enable_totp(
        db, uuid.UUID(token_payload["sub"]), payload.code
    )
    return MessageResponse(message="Two-factor authentication has been enabled.")


# ── Google OAuth ──────────────────────────────────────────────────────────────

@router.get(
    "/google",
    summary="Initiate Google OAuth login",
    include_in_schema=True,
)
async def google_login() -> dict:
    """Returns the Google OAuth redirect URL. Frontend redirects the user there."""
    # Full OAuth implementation in Block 2 extension — requires Google client setup
    return {"message": "Google OAuth — configure GOOGLE_CLIENT_ID in .env to enable."}


# ── Helpers ────────────────────────────────────────────────────────────────────

def _set_refresh_cookie(response: Response, token: str) -> None:
    params = get_cookie_params()
    key = params.pop("key")
    response.set_cookie(value=token, **{k: v for k, v in params.items()}, key=key)


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        key=REFRESH_TOKEN_COOKIE_NAME,
        path="/api/v1/auth",
        secure=True,
        httponly=True,
        samesite="strict",
    )


def _get_ip(request: Request) -> str | None:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None