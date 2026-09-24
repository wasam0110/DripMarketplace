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
    Runs 30 minutes after a COD order is placed.
    Auto-cancels if status is still pending_cod_verification.

    Business rule: BR-COD-02 — COD orders not verified within 30 min are cancelled.
    """
    from sqlalchemy.ext.asyncio import AsyncSession
    from app.core.database import AsyncSessionLocal
    from app.models.order import OrderStatus
    from app.repositories.order_repo import OrderRepository, SellerOrderRepository
    from app.repositories.inventory_repo import InventoryRepository
    from app.models.order import SellerOrderStatus

    async with AsyncSessionLocal() as db:
        try:
            order_repo = OrderRepository(db)
            so_repo    = SellerOrderRepository(db)
            inv_repo   = InventoryRepository(db)

            order = await order_repo.get_by_id(UUID(order_id), for_update=True)
            if not order:
                logger.warning(f"COD timeout: order {order_id} not found")
                return

            if order.status != OrderStatus.pending_cod_verification:
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
            for item in order.items:
                await inv_repo.release(item.variant_id, item.quantity)

            # Cancel seller orders
            for so in order.seller_orders:
                await so_repo.update_status(so.id, SellerOrderStatus.cancelled)

            # Cancel order
            await order_repo.update_status(
                order.id,
                OrderStatus.cancelled,
                note="Auto-cancelled: COD verification deadline expired",
            )
            await db.commit()
            logger.info(f"COD timeout: order {order_id} auto-cancelled")

        except Exception as exc:
            await db.rollback()
            logger.error(f"COD timeout task failed for order {order_id}: {exc}")
            raise


async def send_order_confirmation(ctx: dict, order_id: str) -> None:
    from app.core.database import AsyncSessionLocal
    from app.services.notification_service import NotificationService
    async with AsyncSessionLocal() as db:
        try:
            await NotificationService(db).notify_order_placed(UUID(order_id))
        except Exception as exc:
            logger.error(f"Order confirmation failed for {order_id}: {exc}")

async def expire_pending_orders(ctx: dict) -> None:
    """Sweep expired reservations; no per-order queue job needs to survive an outage."""
    from datetime import UTC, datetime, timedelta
    from sqlalchemy import select, or_, and_
    from app.core.config import settings
    from app.core.database import AsyncSessionLocal
    from app.models.order import Order, OrderStatus, SellerOrderStatus
    from app.repositories.order_repo import OrderRepository, SellerOrderRepository
    from app.repositories.inventory_repo import InventoryRepository
    now = datetime.now(UTC)
    async with AsyncSessionLocal() as db:
        from app.services.platform_settings import get_platform_settings
        policy = await get_platform_settings(db)
        ids = list((await db.scalars(select(Order.id).where(or_(
            and_(Order.status == OrderStatus.pending_cod_verification, Order.created_at < now - timedelta(minutes=policy.cod_timeout_minutes)),
            and_(Order.status == OrderStatus.pending_payment, Order.created_at < now - timedelta(minutes=settings.PAYMENT_TIMEOUT_MINUTES))
        )).order_by(Order.created_at).limit(100).with_for_update(skip_locked=True))).all())
        for order_id in ids:
            order = await OrderRepository(db).get_by_id(order_id)
            for item in order.items:
                await InventoryRepository(db).release(item.variant_id, item.quantity)
            for seller_order in order.seller_orders:
                await SellerOrderRepository(db).update_status(seller_order.id, SellerOrderStatus.cancelled)
            await OrderRepository(db).update_status(order.id, OrderStatus.cancelled, note="Payment or COD verification deadline expired")
        await db.commit()
