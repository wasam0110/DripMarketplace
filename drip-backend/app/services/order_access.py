"""Scoped guest capability: an email address is never an authorization credential."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from jose import JWTError, jwt

from app.core.config import settings
from app.core.exceptions import NotFoundError, AuthenticationError
from app.core.security import _load_private_key, _load_public_key
from app.repositories.order_repo import OrderRepository


def create_guest_token(order_id: UUID) -> str:
    now = datetime.now(UTC)
    return jwt.encode(
        {
            "sub": str(order_id),
            "aud": "wearhowz-guest-order",
            "iss": "wearhowz-api",
            "iat": now,
            "exp": now + timedelta(days=settings.GUEST_ORDER_TOKEN_DAYS),
        },
        _load_private_key(),
        algorithm="RS256",
    )


def guest_token_matches(token: str | None, order_id: UUID) -> bool:
    if not token:
        return False
    try:
        claims = jwt.decode(
            token,
            _load_public_key(),
            algorithms=["RS256"],
            audience="wearhowz-guest-order",
            issuer="wearhowz-api",
            options={"require_exp": True, "require_sub": True},
        )
        return claims["sub"] == str(order_id)
    except JWTError:
        return False


async def authorized_order(db, order_id, user_id=None, guest_token=None, *, lock=False):
    if user_id is None and not guest_token:
        raise AuthenticationError("Sign in or provide a guest order token")
    order = await OrderRepository(db).get_by_id(order_id, for_update=lock)
    allowed = order is not None and (
        (order.user_id is not None and order.user_id == user_id)
        or (order.user_id is None and guest_token_matches(guest_token, order.id))
    )
    if not allowed:
        raise NotFoundError("Order not found")
    return order
