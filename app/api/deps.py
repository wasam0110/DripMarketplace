"""
app/api/deps.py
───────────────
FastAPI dependencies injected into route handlers.

Usage pattern (thin routes — all logic in services):
    @router.get("/resource")
    async def handler(
        db:           AsyncSession = Depends(get_db),
        current_user: User         = Depends(get_current_user),
    ):
        return await some_service.do_thing(db, current_user)
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import Cookie, Depends, Header, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import (
    AuthenticationError,
    EmailNotVerifiedError,
    PermissionDeniedError,
    SellerNotActiveError,
    SellerSuspendedError,
    TokenExpiredError,
    TokenInvalidError,
)
from app.core.security import decode_access_token, is_token_revoked
from app.core.logging import get_logger

logger = get_logger(__name__)

# ── Re-export db dependency ───────────────────────────────────────────────────
DBSession = Annotated[AsyncSession, Depends(get_db)]

# ── Bearer token extractor ────────────────────────────────────────────────────
_bearer = HTTPBearer(auto_error=False)


async def _extract_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> str | None:
    """Extract Bearer token from Authorization header. Returns None if absent."""
    if credentials and credentials.scheme.lower() == "bearer":
        return credentials.credentials
    return None


# ── Token validation ──────────────────────────────────────────────────────────

async def _validate_token(token: str | None) -> dict:
    """
    Decode and validate the access token.
    Checks: signature, expiry, audience, issuer, revocation list.
    Raises the appropriate DRIPException on any failure.
    """
    if not token:
        raise AuthenticationError(message="Authentication token required.")

    # Decode and verify signature + claims
    try:
        payload = decode_access_token(token)
    except (TokenExpiredError, TokenInvalidError):
        raise

    # Check revocation list
    jti = payload.get("jti")
    if jti and await is_token_revoked(jti):
        raise TokenInvalidError(message="Token has been revoked.")

    return payload


# ── User fetching ─────────────────────────────────────────────────────────────

async def get_current_user_payload(
    token: str | None = Depends(_extract_token),
) -> dict:
    """
    Validate the access token and return the decoded payload.
    Used by role-specific dependencies below.
    """
    return await _validate_token(token)


async def get_optional_user_payload(
    token: str | None = Depends(_extract_token),
) -> dict | None:
    """
    Like get_current_user_payload but returns None for unauthenticated requests.
    Used on endpoints that optionally personalise for logged-in users.
    """
    if not token:
        return None
    try:
        return await _validate_token(token)
    except Exception:
        return None


# ── Role-based dependencies ───────────────────────────────────────────────────

async def require_customer(
    payload: dict = Depends(get_current_user_payload),
) -> dict:
    """Require any authenticated user (customer, seller, or admin)."""
    return payload


async def require_seller(
    db: AsyncSession = Depends(get_db),
    payload: dict = Depends(get_current_user_payload),
) -> dict:
    """
    Require an authenticated seller with an active brand account.
    Injects seller_id into the payload for convenience.
    """
    role = payload.get("role")
    if role not in ("seller", "admin"):
        raise PermissionDeniedError(
            message="A seller account is required to perform this action."
        )

    if role == "seller":
        # Verify seller status (lazy import to avoid circular deps)
        from app.repositories.seller_repo import SellerRepository
        seller = await SellerRepository(db).get_by_user_id(UUID(payload["sub"]))
        if not seller:
            raise PermissionDeniedError(message="Seller account not found.")
        if seller.status.value == "suspended":
            raise SellerSuspendedError()
        if seller.status.value not in ("active",):
            raise SellerNotActiveError()
        payload["seller_id"] = str(seller.id)

    return payload


async def require_admin(
    payload: dict = Depends(get_current_user_payload),
) -> dict:
    """Require an admin user. Most restrictive — admins only."""
    if payload.get("role") != "admin":
        raise PermissionDeniedError(
            message="Administrator access is required."
        )
    return payload


# ── Ownership verification helpers ───────────────────────────────────────────

def assert_owns_resource(
    payload: dict,
    resource_user_id: UUID | str,
    allow_admin: bool = True,
) -> None:
    """
    Raise PermissionDeniedError if the current user doesn't own the resource.
    Admins bypass this check if allow_admin=True.
    """
    user_id = payload.get("sub")
    role    = payload.get("role")
    if allow_admin and role == "admin":
        return
    if str(user_id) != str(resource_user_id):
        raise PermissionDeniedError()


def assert_owns_seller_resource(
    payload: dict,
    resource_seller_id: UUID | str,
) -> None:
    """
    Raise PermissionDeniedError if the seller token doesn't own the seller resource.
    Admins bypass.
    """
    role = payload.get("role")
    if role == "admin":
        return
    seller_id = payload.get("seller_id")
    if not seller_id or str(seller_id) != str(resource_seller_id):
        raise PermissionDeniedError()


# ── Typed dependency aliases (for clean route signatures) ─────────────────────

CurrentUser   = Annotated[dict, Depends(require_customer)]
CurrentSeller = Annotated[dict, Depends(require_seller)]
CurrentAdmin  = Annotated[dict, Depends(require_admin)]
OptionalUser  = Annotated[dict | None, Depends(get_optional_user_payload)]