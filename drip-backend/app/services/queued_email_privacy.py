"""Send-time identity checks for legacy raw-address email jobs.

Keep old job signatures readable, but never use a queued address alone as proof
of identity. Hold the user lock through provider handoff so customer deletion
and delivery serialize. Queue payloads are still sensitive while pending.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from hashlib import sha256
from uuid import UUID

from arq import Retry
from sqlalchemy import select

from app.core.exceptions import TokenInvalidError
from app.core.logging import get_logger
from app.core.security import decode_email_verify_token, decode_password_reset_token
from app.models.order import Order
from app.models.seller import Seller, SellerStatus
from app.models.user import User, UserRole

logger = get_logger(__name__)


@asynccontextmanager
async def checked_email_recipient(
    ctx: dict,
    email: str,
    *,
    token: str | None = None,
    purpose: str | None = None,
    order_number: str | None = None,
    brand_name: str | None = None,
    order_updates: bool = False,
) -> AsyncIterator[str | None]:
    """Yield current recipient name, or None for obsolete/unverifiable jobs.

    Infrastructure failures retry; invalid credentials and deleted/mismatched
    recipients do not. Session exit releases locks without committing caller state.
    """
    from app.core.database import AsyncSessionLocal
    from app.core.redis import get_redis

    # Match the application's case-insensitive account lookup convention.
    email = email.lower().strip()
    user_id = None
    if purpose is not None:
        decoder = {
            "verification": decode_email_verify_token,
            "password_reset": decode_password_reset_token,
        }.get(purpose)
        try:
            if decoder is None or token is None:
                raise ValueError("Unsupported email credential")
            user_id = UUID(decoder(token))
        except (TokenInvalidError, ValueError, TypeError, AttributeError):
            logger.info("email.obsolete_job", skip_code="invalid_token")
            yield None
            return

    try:
        async with AsyncSessionLocal() as db:
            if order_number is not None:
                order = await db.scalar(select(Order).where(Order.order_number == order_number))
                if order is None:
                    yield None
                    return
                user_id = order.user_id
                if user_id is None:
                    # Guest ownership belongs to this order, not a same-email account.
                    matches = (order.guest_email or "").lower().strip() == email
                    yield (order.guest_name or "there") if matches else None
                    return

            if user_id is None and brand_name is None:
                yield None
                return
            condition = User.id == user_id if user_id is not None else User.email == email
            user = await db.scalar(
                select(User)
                .where(condition)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
            if user is None or user.deleted_at is not None or user.email.lower().strip() != email:
                logger.info("email.obsolete_job", skip_code="recipient_unavailable")
                yield None
                return
            if purpose == "verification" and user.has_verified_email:
                yield None
                return
            if purpose == "password_reset":
                assert token is not None  # Validated above before opening the session.
                used_key = "password-reset-used:" + sha256(token.encode()).hexdigest()
                if await get_redis().exists(used_key):
                    yield None
                    return
            if brand_name is not None:
                seller = await db.scalar(
                    select(Seller).where(
                        Seller.user_id == user.id,
                        Seller.brand_name == brand_name,
                        Seller.status == SellerStatus.active,
                        Seller.deleted_at.is_(None),
                    )
                )
                if user.role != UserRole.seller or seller is None:
                    yield None
                    return
            if order_updates:
                from app.services.legacy_preferences import import_legacy_preferences

                prefs = await import_legacy_preferences(db, user.id)
                if not prefs.order_updates_email:
                    yield None
                    return
            yield user.first_name or "there"
    except Retry:
        raise
    except Exception as exc:
        # Do not log addresses, names, tokens, SQL parameters or provider messages.
        logger.warning("email.delivery_check_failed", error_type=type(exc).__name__)
        raise Retry(defer=30 * ctx.get("job_try", 1)) from exc
