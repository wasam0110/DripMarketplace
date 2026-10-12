"""
app/tasks/wallet_tasks.py — ARQ background tasks for wallet & commission
Block 7: Wallet & Commission
"""
from __future__ import annotations

import logging
from uuid import UUID
from decimal import Decimal

logger = logging.getLogger(__name__)


async def settle_commission(ctx: dict, seller_order_id: str) -> None:
    """
    Settle commission for a delivered SellerOrder.
    Called when seller_order status changes to 'delivered'.
    Business rule: 15% commission to DRIP, 85% to seller (held 3 days).
    """
    from app.core.database import AsyncSessionLocal
    from app.services.commission_service import CommissionService

    async with AsyncSessionLocal() as db:
        try:
            await CommissionService(db).settle(UUID(seller_order_id))
            logger.info(f"Commission settled for seller_order {seller_order_id}")
        except Exception as exc:
            await db.rollback()
            logger.error(f"Commission settlement failed for {seller_order_id}: {exc}")
            raise


async def move_pending_to_available(ctx: dict, seller_id: str | None = None, amount_str: str | None = None) -> None:
    """Release only mature, unreleased ledger entries. Legacy job arguments are hints only."""
    from app.core.database import AsyncSessionLocal
    from app.services.commission_service import CommissionService

    async with AsyncSessionLocal() as db:
        await CommissionService(db).release_mature()
