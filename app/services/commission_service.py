from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessRuleError, NotFoundError
from app.models.wallet import WalletTxType
from app.repositories.wallet_repo import CommissionRepository, WalletTransactionRepository
from app.repositories.seller_repo import WalletRepository

COMMISSION_RATE  = Decimal("0.15")   # 15%
WALLET_HOLD_DAYS = 3


class CommissionService:
    def __init__(self, db: AsyncSession) -> None:
        self.db         = db
        self.comm_repo  = CommissionRepository(db)
        self.tx_repo    = WalletTransactionRepository(db)
        self.wallet_repo = WalletRepository(db)

    async def settle(self, seller_order_id: UUID) -> None:
        """
        Called when a SellerOrder is marked delivered.
        1. Create CommissionLedger entry (idempotent — skips if already settled)
        2. Credit seller pending_balance
        3. Log WalletTransaction
        4. Enqueue 3-day hold release task
        """
        if await self.comm_repo.exists_for_seller_order(seller_order_id):
            return  # Already settled — idempotent

        from sqlalchemy import select
        from app.models.order import SellerOrder
        result = await self.db.execute(
            select(SellerOrder).where(SellerOrder.id == seller_order_id)
        )
        seller_order = result.scalar_one_or_none()
        if not seller_order:
            raise NotFoundError(f"SellerOrder {seller_order_id} not found")

        gross_amount      = seller_order.subtotal
        commission_amount = (gross_amount * COMMISSION_RATE).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        seller_amount     = gross_amount - commission_amount

        # CommissionLedger
        await self.comm_repo.create(
            seller_order_id   = seller_order_id,
            seller_id         = seller_order.seller_id,
            gross_amount      = gross_amount,
            commission_rate   = COMMISSION_RATE,
            commission_amount = commission_amount,
            seller_amount     = seller_amount,
        )

        # Credit pending_balance in SellerWallet
        wallet = await self.wallet_repo.get_by_seller_id(seller_order.seller_id)
        if not wallet:
            raise NotFoundError("Seller wallet not found")

        await self.wallet_repo.credit_pending(seller_order.seller_id, seller_amount)
        await self.wallet_repo.charge_commission(seller_order.seller_id, commission_amount)

        # Refresh to get updated balance
        from sqlalchemy import select as sa_select
        from app.models.seller import SellerWallet
        wresult = await self.db.execute(
            sa_select(SellerWallet).where(SellerWallet.seller_id == seller_order.seller_id)
        )
        updated_wallet = wresult.scalar_one()
        balance_after  = updated_wallet.pending_balance

        # WalletTransaction log
        await self.tx_repo.create(
            seller_id       = seller_order.seller_id,
            type            = WalletTxType.credit_commission,
            amount          = seller_amount,
            balance_after   = balance_after,
            reference       = str(seller_order_id),
            seller_order_id = seller_order_id,
            note            = f"Commission settled: PKR {int(gross_amount):,} × {int(COMMISSION_RATE * 100)}% = PKR {int(commission_amount):,} DRIP, PKR {int(seller_amount):,} seller",
        )

        await self.db.commit()

        # Enqueue hold release after 3 days
        await self._enqueue_release(seller_order.seller_id, seller_amount)

    async def _enqueue_release(self, seller_id: UUID, amount: Decimal) -> None:
        try:
            from datetime import timedelta
            from arq import create_pool
            from arq.connections import RedisSettings
            from app.core.config import settings
            pool = await create_pool(RedisSettings.from_dsn(str(settings.REDIS_URL)))
            await pool.enqueue_job(
                "move_pending_to_available",
                str(seller_id),
                str(amount),
                _defer_by=WALLET_HOLD_DAYS * 24 * 3600,
            )
            await pool.aclose()
        except Exception:
            pass  # Non-critical — can be triggered manually