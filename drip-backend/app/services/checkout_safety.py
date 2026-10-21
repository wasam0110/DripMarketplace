"""Signed price acceptance and durable, owner-scoped checkout replay protection.

The HTTP boundary requires both checkout_key and quote_token. A UUID4 key is a
guest recovery capability: never log it or place it in a URL. Only its scoped hash
is stored, in the same SQL commit as inventory, coupon usage and the order.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

import jwt
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.core.security import _load_private_key, _load_public_key
from app.models.order import Order, PaymentMethod
from app.schemas.order import CheckoutOrderRequest, GuestCheckoutOrderRequest

if TYPE_CHECKING:
    from app.services.order_service import _CheckoutCalculation

QUOTE_TTL = timedelta(minutes=15)
GUEST_RECOVERY_TTL = timedelta(hours=24)


def digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def key_hash(key: UUID, user_id: UUID | None) -> str:
    return digest(["checkout-v1", str(user_id) if user_id else "guest", str(key)])


def price_fingerprint(
    calculation: _CheckoutCalculation,
    discount: Decimal,
    coupon_code: str | None,
    payment_method: PaymentMethod,
) -> str:
    """Bind exact lines, per-line prices, shipping, discount and payment selection."""

    def money(value: Decimal) -> str:
        return format(value, ".2f")

    return digest(
        {
            "lines": sorted(
                [
                    [
                        str(line.variant.id),
                        str(line.variant.product.id),
                        str(line.variant.product.seller_id),
                        line.variant.size_value,
                        line.variant.colour,
                        line.quantity,
                        money(line.unit_price),
                    ]
                    for line in calculation.lines
                ]
            ),
            "subtotal": money(calculation.subtotal),
            "shipping": money(calculation.shipping_fee),
            "discount": money(discount),
            "coupon": (coupon_code or "").upper(),
            "method": str(payment_method.value),
        }
    )


def sign_quote(fingerprint: str, user_id: UUID | None) -> tuple[str, datetime]:
    now = datetime.now(UTC)
    expires = now + QUOTE_TTL
    token = jwt.encode(
        {
            "sub": str(user_id) if user_id else "guest",
            "aud": "wearhowz-checkout-quote",
            "iss": "wearhowz-api",
            "iat": now,
            "exp": expires,
            "price": fingerprint,
        },
        _load_private_key(),
        algorithm="RS256",
    )
    return token, expires


def verify_quote(token: str, user_id: UUID | None) -> str:
    try:
        claims = jwt.decode(
            token,
            _load_public_key(),
            algorithms=["RS256"],
            audience="wearhowz-checkout-quote",
            issuer="wearhowz-api",
            options={"require": ["sub", "iat", "exp", "price"]},
        )
        if claims["sub"] != (str(user_id) if user_id else "guest"):
            raise ValueError("Wrong quote owner")
        if not isinstance(claims["price"], str) or len(claims["price"]) != 64:
            raise ValueError("Invalid price fingerprint")
        return claims["price"]
    except (jwt.PyJWTError, ValueError, TypeError) as exc:
        raise ConflictError(
            "Your quote is invalid or expired. Refresh and accept a new quote.",
            code="CHECKOUT_QUOTE_INVALID",
        ) from exc


@dataclass(frozen=True)
class CheckoutGuard:
    key_hash: str
    request_hash: str
    price: str

    def accept(self, fingerprint: str) -> None:
        if self.price != fingerprint:
            raise ConflictError(
                "Items, prices or delivery changed. Refresh and accept a new quote.",
                code="CHECKOUT_QUOTE_CHANGED",
            )


async def find_order(
    db: AsyncSession,
    key: UUID,
    user_id: UUID | None,
    *,
    lock: bool = False,
) -> Order | None:
    hashed = key_hash(key, user_id)
    if lock:
        # Non-blocking lock bounds request latency; a hash collision only serializes
        # unrelated requests. The full unique index is the durable final safeguard.
        lock_id = int.from_bytes(bytes.fromhex(hashed)[:8], byteorder="big", signed=True)
        acquired = await db.scalar(text("SELECT pg_try_advisory_xact_lock(:key)"), {"key": lock_id})
        if not acquired:
            raise ConflictError(
                "Checkout is still processing. Recover or retry with the same key.",
                code="CHECKOUT_IN_PROGRESS",
            )
    order = await db.scalar(
        select(Order)
        .where(Order.checkout_key_hash == hashed)
        .execution_options(populate_existing=True)
    )
    if order is not None:
        if order.user_id != user_id:
            raise NotFoundError("Checkout")
        created = (
            order.created_at.replace(tzinfo=UTC)
            if order.created_at.tzinfo is None
            else order.created_at
        )
        if user_id is None and datetime.now(UTC) > created + GUEST_RECOVERY_TTL:
            # Keep the key forever for deduplication; never treat expiry as a new order.
            raise ConflictError(
                "Guest recovery has expired. "
                "Use your existing order access link or contact support.",
                code="CHECKOUT_RECOVERY_EXPIRED",
            )
    return order


async def begin_checkout(
    db: AsyncSession,
    payload: CheckoutOrderRequest | GuestCheckoutOrderRequest,
    user_id: UUID | None,
) -> tuple[Order | None, CheckoutGuard | None]:
    order = await find_order(db, payload.checkout_key, user_id, lock=True)
    fingerprint = digest(payload.model_dump(mode="json", exclude={"checkout_key"}))
    if order is not None:
        if order.checkout_request_hash != fingerprint:
            raise ConflictError(
                "This checkout key was already used for different details.",
                code="CHECKOUT_KEY_REUSED",
            )
        return order, None
    return None, CheckoutGuard(
        key_hash(payload.checkout_key, user_id),
        fingerprint,
        verify_quote(payload.quote_token, user_id),
    )
