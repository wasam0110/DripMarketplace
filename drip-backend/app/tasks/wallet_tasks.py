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
    from datetime import UTC, datetime, timedelta
    from sqlalchemy import select
    from app.core.config import settings
    from app.core.database import AsyncSessionLocal
    from app.models.wallet import CommissionLedger, WalletTxType
    from app.models.seller import SellerWallet
    from app.models.order import SellerOrder
    from app.models.payment import Payment, Refund
    from app.repositories.wallet_repo import WalletTransactionRepository
    now = datetime.now(UTC)
    async with AsyncSessionLocal() as db:
        from app.services.platform_settings import get_platform_settings
        policy = await get_platform_settings(db)
        rows = (await db.scalars(select(CommissionLedger).where(
            CommissionLedger.released_at.is_(None),
            CommissionLedger.settled_at <= now - timedelta(days=policy.wallet_hold_days)
        ).with_for_update(skip_locked=True))).all()
        for ledger in rows:
            so = await db.get(SellerOrder, ledger.seller_order_id)
            refund = await db.scalar(select(Refund.id).join(Payment).where(Payment.order_id == so.order_id).limit(1))
            if refund or so.status.value != "delivered":
                continue  # Hold disputed/refunded orders for explicit reconciliation.
            wallet = await db.scalar(select(SellerWallet).where(SellerWallet.seller_id == ledger.seller_id).with_for_update())
            if wallet is None or wallet.pending_balance < ledger.seller_amount:
                continue
            wallet.pending_balance -= ledger.seller_amount
            wallet.available_balance += ledger.seller_amount
            ledger.released_at = now
            await WalletTransactionRepository(db).create(seller_id=ledger.seller_id,
                type=WalletTxType.credit_adjustment, amount=ledger.seller_amount,
                balance_after=wallet.available_balance, reference=str(ledger.id),
                note="Settlement hold released")
        await db.commit()
