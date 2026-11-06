"""
app/tasks/order_tasks.py — ARQ background tasks for orders
Block 5: Cart & Orders

Tasks registered in app/tasks/worker.py
"""

from __future__ import annotations

import logging
from uuid import UUID

logger = logging.getLogger(__name__)


async def cod_verification_timeout(ctx: dict, order_id: str) -> None:
    """
    Auto-cancel a still-pending COD order after its current runtime deadline.
    A policy extension is honoured even when an earlier delayed job fires.
    """
    from app.core.database import AsyncSessionLocal
    from app.models.order import OrderStatus, SellerOrderStatus
    from app.repositories.inventory_repo import InventoryRepository
    from app.repositories.order_repo import OrderRepository, SellerOrderRepository

    async with AsyncSessionLocal() as db:
        try:
            order_repo = OrderRepository(db)
            so_repo = SellerOrderRepository(db)
            inv_repo = InventoryRepository(db)

            order = await order_repo.get_by_id(UUID(order_id), for_update=True)
            if not order:
                logger.warning(f"COD timeout: order {order_id} not found")
                return

            if (
                order.status != OrderStatus.pending_cod_verification
                or order.payment_method != "cod"
            ):
                logger.info(
                    f"COD timeout: order {order_id} already at status {order.status.value} — skip"
                )
                return

            from datetime import UTC, datetime, timedelta

            from app.services.platform_settings import get_platform_settings

            policy = await get_platform_settings(db)
            if order.created_at + timedelta(minutes=policy.cod_timeout_minutes) > datetime.now(UTC):
                return  # A settings change extended the window; the periodic sweep will retry.

            # Release inventory
            for item in sorted(order.items, key=lambda row: row.variant_id):
                await inv_repo.release(item.variant_id, item.quantity, strict=True)

            # Cancel seller orders
            for so in order.seller_orders:
                await so_repo.update_status(so.id, SellerOrderStatus.cancelled)

            # Cancel order
            await order_repo.update_status(
                order.id,
                OrderStatus.cancelled,
                note="Auto-cancelled: COD verification deadline expired",
            )
            from app.services.notification_outbox import queue_notification

            await queue_notification(
                db,
                f"order:{order.id}:status:cancelled",
                "send_order_status_update",
                str(order.id),
                OrderStatus.cancelled.value,
            )
            await db.commit()
            logger.info(f"COD timeout: order {order_id} auto-cancelled")

        except Exception as exc:
            await db.rollback()
            logger.error(f"COD timeout task failed for order {order_id}: {exc}")
            raise


async def expire_pending_orders(ctx: dict) -> None:
    """Sweep expired reservations; no per-order queue job needs to survive an outage."""
    from datetime import UTC, datetime, timedelta

    from sqlalchemy import and_, or_, select

    from app.core.config import settings
    from app.core.database import AsyncSessionLocal
    from app.models.order import Order, OrderStatus, SellerOrderStatus
    from app.repositories.inventory_repo import InventoryRepository
    from app.repositories.order_repo import OrderRepository, SellerOrderRepository
    from app.services.notification_outbox import queue_notification

    now = datetime.now(UTC)
    async with AsyncSessionLocal() as db:
        from app.services.platform_settings import get_platform_settings

        policy = await get_platform_settings(db)
        ids = list(
            (
                await db.scalars(
                    select(Order.id)
                    .where(
                        or_(
                            and_(
                                Order.status == OrderStatus.pending_cod_verification,
                                Order.payment_method == "cod",
                                Order.created_at
                                < now - timedelta(minutes=policy.cod_timeout_minutes),
                            ),
                            and_(
                                Order.status == OrderStatus.pending_payment,
                                Order.created_at
                                < now - timedelta(minutes=settings.PAYMENT_TIMEOUT_MINUTES),
                            ),
                        )
                    )
                    .order_by(Order.created_at)
                    .limit(100)
                    .with_for_update(skip_locked=True)
                )
            ).all()
        )
        for order_id in ids:
            order = await OrderRepository(db).get_by_id(order_id)
            for item in sorted(order.items, key=lambda row: row.variant_id):
                await InventoryRepository(db).release(item.variant_id, item.quantity, strict=True)
            for seller_order in order.seller_orders:
                await SellerOrderRepository(db).update_status(
                    seller_order.id, SellerOrderStatus.cancelled
                )
            await OrderRepository(db).update_status(
                order.id, OrderStatus.cancelled, note="Payment or COD verification deadline expired"
            )
            await queue_notification(
                db,
                f"order:{order.id}:status:cancelled",
                "send_order_status_update",
                str(order.id),
                OrderStatus.cancelled.value,
            )
        await db.commit()
