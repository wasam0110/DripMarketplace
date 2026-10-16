"""One-time conservative bridge from the old Redis hash to durable preferences."""

import asyncio
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ExternalServiceError
from app.core.redis import get_redis
from app.models.notification import NotificationPreference

LEGACY_FIELDS = {
    "email_order_updates": "order_updates_email",
    "email_promotions": "promotions_email",
    "email_new_arrivals": "email_new_arrivals",
    "sms_order_updates": "sms_order_updates",
    "whatsapp_order_updates": "whatsapp_order_updates",
}


async def import_legacy_preferences(db: AsyncSession, user_id: UUID) -> NotificationPreference:
    """Caller owns commit. Retain Redis data for rollback; never overwrite later edits."""
    from app.services.account_lifecycle import lock_active_user

    await lock_active_user(db, user_id)
    inserted = await db.execute(
        insert(NotificationPreference)
        .values(user_id=user_id)
        .on_conflict_do_nothing(index_elements=["user_id"])
    )
    prefs = await db.scalar(
        select(NotificationPreference)
        .where(NotificationPreference.user_id == user_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if prefs.legacy_imported:
        return prefs
    try:
        async with asyncio.timeout(3):
            raw = await get_redis().hgetall(f"notif_prefs:{user_id}")
        decoded = {
            key.decode() if isinstance(key, bytes) else key: value.decode()
            if isinstance(value, bytes)
            else value
            for key, value in raw.items()
        }
        for old, new in LEGACY_FIELDS.items():
            if old not in decoded:
                continue
            value = decoded[old]
            if value not in ("0", "1", "true", "false"):
                raise ValueError("Invalid legacy preference")
            enabled = value in ("1", "true")
            setattr(prefs, new, enabled if inserted.rowcount else getattr(prefs, new) and enabled)
    except Exception as exc:
        raise ExternalServiceError("Notification preferences are temporarily unavailable") from exc
    prefs.legacy_imported = True
    await db.flush()
    return prefs
