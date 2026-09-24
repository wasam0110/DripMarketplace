"""Google authorization code flow, with browser-bound state, nonce and PKCE.
References: https://developers.google.com/identity/openid-connect/openid-connect
"""

import base64
import hashlib
import hmac
import json
import secrets
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode

import httpx
from jose import JWTError, jwt
from fastapi.responses import RedirectResponse

from app.core.config import settings
from app.core.exceptions import AuthenticationError, BusinessRuleError, ExternalServiceError
from app.core.redis import get_redis
from app.core.security import generate_refresh_token, hash_refresh_token, get_cookie_params
from app.models.user import UserRole
from app.repositories.user_repo import UserRepository, SessionRepository

STATE_COOKIE = "wearhowz_oauth_state"
CALLBACK_PATH = "/api/v1/auth/google/callback"


def require_configuration():
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise ExternalServiceError("Google sign-in is not configured")


async def start_google_login(response):
    require_configuration()
    state, nonce, verifier = (secrets.token_urlsafe(32) for _ in range(3))
    challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    )
    await get_redis().setex(
        "google-state:" + state, 600, json.dumps({"nonce": nonce, "verifier": verifier})
    )
    response.set_cookie(
        STATE_COOKIE,
        state,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        max_age=600,
        path=CALLBACK_PATH,
    )
    response.headers["Cache-Control"] = "no-store"
    return {
        "authorization_url": "https://accounts.google.com/o/oauth2/v2/auth?"
        + urlencode(
            {
                "client_id": settings.GOOGLE_CLIENT_ID,
                "redirect_uri": settings.API_BASE_URL + CALLBACK_PATH,
                "response_type": "code",
                "scope": "openid email profile",
                "state": state,
                "nonce": nonce,
                "code_challenge": challenge,
                "code_challenge_method": "S256",
            }
        )
    }


async def finish_google_login(request, db):
    require_configuration()
    state = request.query_params.get("state", "")
    cookie = request.cookies.get(STATE_COOKIE, "")
    code = request.query_params.get("code", "")
    if (
        not state
        or not cookie
        or len(state) > 128
        or not hmac.compare_digest(state, cookie)
        or not code
    ):
        raise AuthenticationError("Google sign-in state is invalid")
    stored = await get_redis().getdel("google-state:" + state)
    if not stored:
        raise AuthenticationError("Google sign-in expired; please try again")
    flow = json.loads(stored)
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            token_response = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "code": code,
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "redirect_uri": settings.API_BASE_URL + CALLBACK_PATH,
                    "grant_type": "authorization_code",
                    "code_verifier": flow["verifier"],
                },
            )
            token_response.raise_for_status()
            keys = await client.get("https://www.googleapis.com/oauth2/v3/certs")
            keys.raise_for_status()
        claims = jwt.decode(
            token_response.json()["id_token"],
            keys.json(),
            algorithms=["RS256"],
            audience=settings.GOOGLE_CLIENT_ID,
            options={"require_exp": True, "require_sub": True, "require_iat": True},
        )
        if claims.get("iss") not in ("accounts.google.com", "https://accounts.google.com"):
            raise AuthenticationError("Google identity issuer is invalid")
        if claims.get("azp", settings.GOOGLE_CLIENT_ID) != settings.GOOGLE_CLIENT_ID:
            raise AuthenticationError("Google identity audience is invalid")
        if not hmac.compare_digest(str(claims.get("nonce", "")), flow["nonce"]):
            raise AuthenticationError("Google identity nonce is invalid")
        if claims.get("email_verified") is not True or not claims.get("email"):
            raise AuthenticationError("Google email must be verified")
    except (httpx.HTTPError, JWTError, KeyError, ValueError) as exc:
        raise AuthenticationError("Google sign-in could not be verified") from exc
    user = await UserRepository.get_by_google_id(db, claims["sub"])
    if user is None:
        existing = await UserRepository.get_by_email(db, claims["email"])
        if existing:
            # Email equality alone does not authorize linking an existing account.
            raise BusinessRuleError(
                "An account already uses this email. Sign in with its existing method."
            )
        user = await UserRepository.create(
            db,
            email=claims["email"].lower(),
            google_id=claims["sub"],
            first_name=claims.get("given_name", "")[:100],
            last_name=claims.get("family_name", "")[:100],
            role=UserRole.customer,
            has_verified_email=True,
        )
    if user.deleted_at is not None or user.role != UserRole.customer or user.is_2fa_enabled:
        raise AuthenticationError("Use the account's existing sign-in method")
    refresh = generate_refresh_token()
    await SessionRepository.create(
        db,
        user_id=user.id,
        token_hash=hash_refresh_token(refresh),
        expires_at=datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    await db.commit()
    # No bearer tokens in URLs. The frontend obtains one through POST /auth/refresh.
    response = RedirectResponse(settings.FRONTEND_URL + "/auth/callback", status_code=303)
    response.set_cookie(value=refresh, **get_cookie_params())
    response.delete_cookie(STATE_COOKIE, path=CALLBACK_PATH)
    response.headers["Cache-Control"] = "no-store"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response
