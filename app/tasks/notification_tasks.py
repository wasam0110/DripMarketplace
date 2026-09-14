"""
app/tasks/notification_tasks.py — ARQ notification background tasks
Block 9: Notifications
"""
from __future__ import annotations

import logging
from uuid import UUID
from typing import Optional

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


async def notify_seller_decision(
    ctx: dict, seller_id: str, approved: bool, reason: Optional[str] = None
) -> None:
    """Notify seller of approval or rejection."""
    from app.core.database import AsyncSessionLocal
    from app.services.notification_service import NotificationService

    async with AsyncSessionLocal() as db:
        try:
            await NotificationService(db).notify_seller_decision(
                UUID(seller_id), approved, reason
            )
        except Exception as exc:
            logger.error(f"Seller decision notification failed: {exc}")


async def broadcast_notification(
    ctx:        dict,
    user_ids:   list[str],
    title:      str,
    body:       str,
    action_url: Optional[str],
    task_id:    str,
) -> None:
    """Fan-out broadcast notification to a list of user IDs."""
    from app.core.database import AsyncSessionLocal
    from app.services.notification_service import NotificationService, NotifType

    async with AsyncSessionLocal() as db:
        svc   = NotificationService(db)
        count = 0
        for uid_str in user_ids:
            try:
                await svc.repo.create(
                    user_id    = UUID(uid_str),
                    type       = NotifType.BROADCAST,
                    title      = title,
                    body       = body,
                    action_url = action_url,
                )
                count += 1
            except Exception:
                pass

        await db.commit()
        logger.info(f"Broadcast {task_id}: sent to {count}/{len(user_ids)} users")