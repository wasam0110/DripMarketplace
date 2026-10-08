"""
app/tasks/notification_tasks.py — ARQ notification background tasks
Block 9: Notifications
"""

from __future__ import annotations

import logging
from uuid import NAMESPACE_URL, UUID, uuid5
from typing import Optional

from arq import Retry

logger = logging.getLogger(__name__)


async def send_order_confirmation(ctx: dict, order_id: str) -> None:
    """Send order confirmation email + in-app notification."""
    from app.core.database import AsyncSessionLocal
    from app.services.notification_service import NotificationService

    async with AsyncSessionLocal() as db:
        try:
            await NotificationService(db).notify_order_placed(UUID(order_id))
            logger.info(f"Order confirmation sent for order {order_id}")
        except Exception as exc:
            logger.error(f"Order confirmation failed for {order_id}: {exc}")
            raise Retry(defer=30 * ctx.get("job_try", 1)) from exc


async def send_order_status_update(ctx: dict, order_id: str, new_status: str) -> None:
    """Notify customer of order status change."""
    from app.core.database import AsyncSessionLocal
    from app.services.notification_service import NotificationService

    async with AsyncSessionLocal() as db:
        try:
            await NotificationService(db).notify_order_status(UUID(order_id), new_status)
            logger.info(f"Status update sent: order {order_id} → {new_status}")
        except Exception as exc:
            logger.error(f"Status update failed: {exc}")
            raise Retry(defer=30 * ctx.get("job_try", 1)) from exc


async def send_payout_notification(ctx: dict, payout_id: str, status: str) -> None:
    """Notify seller of payout status change."""
    from app.core.database import AsyncSessionLocal
    from app.services.notification_service import NotificationService

    async with AsyncSessionLocal() as db:
        try:
            await NotificationService(db).notify_payout(UUID(payout_id), status)
            logger.info(f"Payout notification sent: {payout_id} → {status}")
        except Exception as exc:
            logger.error(f"Payout notification failed: {exc}")
            raise Retry(defer=30 * ctx.get("job_try", 1)) from exc


async def notify_seller_decision(
    ctx: dict, seller_id: str, approved: bool, reason: Optional[str] = None
) -> None:
    """Notify seller of approval or rejection."""
    from app.core.database import AsyncSessionLocal
    from app.services.notification_service import NotificationService

    async with AsyncSessionLocal() as db:
        try:
            await NotificationService(db).notify_seller_decision(UUID(seller_id), approved, reason)
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
) -> None:
    """Fan-out broadcast notification to a list of user IDs."""
    from app.core.database import AsyncSessionLocal
    from sqlalchemy.dialects.postgresql import insert

    from app.models.notification import Notification
    from app.services.notification_service import NotifType

    async with AsyncSessionLocal() as db:
        try:
            count = 0
            for uid_str in user_ids:
                user_id = UUID(uid_str)
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
