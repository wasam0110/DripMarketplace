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

            order = await order_repo.get_by_id(UUID(order_id))
            if not order:
                logger.warning(f"COD timeout: order {order_id} not found")
                return

            if order.status != OrderStatus.pending_cod_verification:
                logger.info(
                    f"COD timeout: order {order_id} already at status {order.status.value} — skip"
                )
                return

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
                note="Auto-cancelled: COD verification timeout (30 min)",
            )
            await db.commit()
            logger.info(f"COD timeout: order {order_id} auto-cancelled")

        except Exception as exc:
            await db.rollback()
            logger.error(f"COD timeout task failed for order {order_id}: {exc}")
            raise


async def send_order_confirmation(ctx: dict, order_id: str) -> None:
    """
    Send order confirmation email to customer.
    Wired with Resend in Block 9 (Notifications).
    """
    logger.info(f"Order confirmation email queued for order {order_id} — wired in Block 9")