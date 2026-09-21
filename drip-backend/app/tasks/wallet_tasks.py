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


async def move_pending_to_available(
    ctx: dict, seller_id: str, amount_str: str
) -> None:
    """
    Move amount from pending_balance to available_balance after 3-day hold.
    Enqueued by commission_service.settle() with _defer_by=3 days.
    """
    from app.core.database import AsyncSessionLocal
    from app.repositories.seller_repo import WalletRepository
    from app.repositories.wallet_repo import WalletTransactionRepository
    from app.models.wallet import WalletTxType

    async with AsyncSessionLocal() as db:
        try:
            seller_uuid = UUID(seller_id)
            amount      = Decimal(amount_str)
            wallet_repo = WalletRepository(db)
            tx_repo     = WalletTransactionRepository(db)

            await wallet_repo.release_pending_to_available(seller_uuid, amount)

            updated       = await wallet_repo.get_by_seller_id(seller_uuid)
            balance_after = updated.available_balance if updated else Decimal("0")

            await tx_repo.create(
                seller_id     = seller_uuid,
                type          = WalletTxType.credit_adjustment,
                amount        = amount,
                balance_after = balance_after,
                note          = "3-day hold released — funds now available for withdrawal",
            )

            await db.commit()
            logger.info(f"Released PKR {amount} from pending to available for seller {seller_id}")

        except Exception as exc:
            await db.rollback()
            logger.error(f"move_pending_to_available failed for {seller_id}: {exc}")
            raise 