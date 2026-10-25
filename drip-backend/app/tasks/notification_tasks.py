"""
app/tasks/notification_tasks.py — ARQ notification background tasks
Block 9: Notifications
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Optional
from uuid import NAMESPACE_URL, UUID, uuid5

from arq import Retry
from sqlalchemy import or_, select

from app.core.logging import get_logger

logger = logging.getLogger(__name__)
audit_logger = get_logger(__name__)

# Exceeds the worker's 300s timeout; stale queue entries may safely be republished.
RECOVERY_DELAY = timedelta(minutes=15)
MAX_PUBLICATIONS = 10
MAX_DELIVERIES = 5


async def send_order_confirmation(
    ctx: dict, order_id: str, event_key: Optional[str] = None
) -> None:
    """Send order confirmation email + in-app notification."""
    from app.core.database import AsyncSessionLocal
    from app.services.notification_service import NotificationService

    async with AsyncSessionLocal() as db:
        try:
            await NotificationService(db).notify_order_placed(UUID(order_id), event_key)
            logger.info(f"Order confirmation sent for order {order_id}")
        except Exception as exc:
            logger.error(f"Order confirmation failed for {order_id}: {exc}")
            raise Retry(defer=30 * ctx.get("job_try", 1)) from exc


async def send_order_status_update(
    ctx: dict, order_id: str, new_status: str, event_key: Optional[str] = None
) -> None:
    """Notify customer of order status change."""
    from app.core.database import AsyncSessionLocal
    from app.services.notification_service import NotificationService

    async with AsyncSessionLocal() as db:
        try:
            await NotificationService(db).notify_order_status(
                UUID(order_id), new_status, event_key
            )
            logger.info(f"Status update sent: order {order_id} → {new_status}")
        except Exception as exc:
            logger.error(f"Status update failed: {exc}")
            raise Retry(defer=30 * ctx.get("job_try", 1)) from exc


async def send_payout_notification(
    ctx: dict, payout_id: str, status: str, event_key: Optional[str] = None
) -> None:
    """Notify seller of payout status change."""
    from app.core.database import AsyncSessionLocal
    from app.services.notification_service import NotificationService

    async with AsyncSessionLocal() as db:
        try:
            await NotificationService(db).notify_payout(UUID(payout_id), status, event_key)
            logger.info(f"Payout notification sent: {payout_id} → {status}")
        except Exception as exc:
            logger.error(f"Payout notification failed: {exc}")
            raise Retry(defer=30 * ctx.get("job_try", 1)) from exc


async def notify_seller_decision(
    ctx: dict,
    seller_id: str,
    approved: bool,
    reason: Optional[str] = None,
    event_key: Optional[str] = None,
) -> None:
    """Notify seller of approval or rejection."""
    from app.core.database import AsyncSessionLocal
    from app.services.notification_service import NotificationService

    async with AsyncSessionLocal() as db:
        try:
            await NotificationService(db).notify_seller_decision(
                UUID(seller_id), approved, reason, event_key
            )
        except Exception as exc:
            logger.error(f"Seller decision notification failed: {exc}")
            raise Retry(defer=30 * ctx.get("job_try", 1)) from exc


async def broadcast_notification(
    ctx: dict,
    user_ids: list[str],
    title: str,
    body: str,
    action_url: Optional[str],
    task_id: str,
    event_key: Optional[str] = None,
) -> None:
    """Fan-out broadcast notification to a list of user IDs."""
    from app.core.database import AsyncSessionLocal
    from sqlalchemy.dialects.postgresql import insert

    from app.models.notification import Notification
    from app.services.notification_service import NotifType

    async with AsyncSessionLocal() as db:
        try:
            count = 0
            from app.models.user import User
            # Stable lock order; deletion cannot race a queued broadcast insert.
            for uid_str in sorted(set(user_ids)):
                user_id = UUID(uid_str)
                user = await db.scalar(select(User).where(User.id == user_id).with_for_update()
                                       .execution_options(populate_existing=True))
                if user is None or user.deleted_at is not None:
                    continue
                notification_id = uuid5(NAMESPACE_URL, f"wearhowz:broadcast:{task_id}:{user_id}")
                statement = (
                    insert(Notification)
                    .values(
                        id=notification_id,
                        user_id=user_id,
                        type=NotifType.BROADCAST,
                        title=title,
                        body=body,
                        action_url=action_url,
                    )
                    .on_conflict_do_nothing(index_elements=[Notification.id])
                )
                result = await db.execute(statement)
                if result.rowcount:
                    count += 1
            await db.commit()
            logger.info(f"Broadcast {task_id}: created {count}/{len(user_ids)} notifications")
        except Exception as exc:
            await db.rollback()
            logger.error(f"Broadcast {task_id} failed: {exc}")
            raise Retry(defer=30 * ctx.get("job_try", 1)) from exc


async def dispatch_notification_outbox(ctx: dict) -> None:
    """Publish committed notification events to ARQ with deterministic job IDs."""
    from app.core.database import AsyncSessionLocal
    from app.models.notification import NotificationOutbox

    first_error: Exception | None = None
    async with AsyncSessionLocal() as db:
        rows = list(
            (
                await db.scalars(
                    select(NotificationOutbox)
                    .where(
                        NotificationOutbox.completed_at.is_(None),
                        NotificationOutbox.dead_lettered_at.is_(None),
                        or_(NotificationOutbox.published_at.is_(None),
                            NotificationOutbox.published_at < datetime.now(UTC) - RECOVERY_DELAY),
                    )
                    .order_by(NotificationOutbox.created_at, NotificationOutbox.id)
                    .limit(100)
                    .with_for_update(skip_locked=True)
                )
            ).all()
        )
        for row in rows:
            if row.attempts >= MAX_PUBLICATIONS:
                row.dead_lettered_at = datetime.now(UTC)
                row.last_error = "publication_budget_exhausted"
                audit_logger.error("notification.outbox_dead_letter", event_id=str(row.id))
                continue
            row.attempts += 1
            try:
                await ctx["redis"].enqueue_job(
                    "deliver_notification_outbox",
                    str(row.id),
                    _job_id=f"notification:{row.id}:{len(row.replay_history)}:{row.attempts}",
                )
            except Exception as exc:
                row.last_error = type(exc).__name__
                first_error = first_error or exc
            else:
                row.last_error = None
                row.published_at = datetime.now(UTC)
        await db.commit()

    if first_error is not None:
        raise Retry(defer=30 * ctx.get("job_try", 1)) from first_error


async def deliver_notification_outbox(ctx: dict, event_id: str) -> None:
    """Serialize all generations of an event; completion survives Redis loss.

    Keep the event row lock while the existing task uses its own session. Those
    tasks commit their keyed delivery records before this completion is recorded.
    A crash in between replays through those keys instead of silently losing work.
    """
    from app.core.database import AsyncSessionLocal
    from app.models.notification import NotificationOutbox
    from app.services.customer_privacy import cleanup_deleted_customer
    from app.services.review_photo_service import cleanup_review_photo

    allowed = {
        "send_order_confirmation": send_order_confirmation,
        "send_order_status_update": send_order_status_update,
        "send_payout_notification": send_payout_notification,
        "notify_seller_decision": notify_seller_decision,
        "broadcast_notification": broadcast_notification,
        "cleanup_deleted_customer": cleanup_deleted_customer,
        "cleanup_review_photo": cleanup_review_photo,
    }
    async with AsyncSessionLocal() as db:
        row = await db.scalar(select(NotificationOutbox).where(
            NotificationOutbox.id == UUID(event_id)).with_for_update())
        if row is None or row.completed_at or row.dead_lettered_at:
            return
        row.delivery_attempts += 1
        try:
            if row.task_name not in allowed:
                raise ValueError("Unsupported outbox task")
            await allowed[row.task_name](ctx, *row.args)
        except Exception as exc:
            row.last_error = type(exc.__cause__ or exc).__name__
            row.published_at = datetime.now(UTC)
            if row.delivery_attempts >= MAX_DELIVERIES or row.task_name not in allowed:
                row.dead_lettered_at = datetime.now(UTC)
                audit_logger.error("notification.outbox_dead_letter", event_id=str(row.id))
        else:
            row.completed_at = datetime.now(UTC)
            row.last_error = None
            if row.task_name == "cleanup_deleted_customer":
                # Do not retain removed asset URLs after successful cleanup.
                row.args = [row.args[0], [], row.event_key]
        await db.commit()
