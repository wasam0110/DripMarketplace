"""Commission settlement and refund reversal accounting."""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID

from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessRuleError, NotFoundError
from app.models.seller import SellerWallet
from app.models.wallet import CommissionLedger, WalletTransaction, WalletTxType
from app.repositories.wallet_repo import CommissionRepository, WalletTransactionRepository
from app.repositories.seller_repo import WalletRepository

# Unit-test default only — runtime always reads from platform_settings.
COMMISSION_RATE  = Decimal("0.15")
WALLET_HOLD_DAYS = 3


class CommissionService:
    def __init__(self, db: AsyncSession) -> None:
        self.db          = db
        self.comm_repo   = CommissionRepository(db)
        self.tx_repo     = WalletTransactionRepository(db)
        self.wallet_repo = WalletRepository(db)

    # ── Settlement ─────────────────────────────────────────────────────────────

    async def settle(self, seller_order_id: UUID, *, commit: bool = True) -> None:
        """
        Credit the seller's pending_balance when a SellerOrder is delivered and paid.

        Idempotent — skips silently if this seller_order already has a ledger entry.

        Edge-case handling: if a refund was confirmed before COD was collected (i.e.
        the return was processed before the platform recorded the cash transfer), the
        confirmed refund total is subtracted from gross before crediting the seller.
        This prevents over-crediting in the rare pay-after-return scenario.
        """
        from app.models.order import SellerOrder
        from app.models.payment import Payment, PaymentStatus, Refund

        result = await self.db.execute(
            select(SellerOrder).where(SellerOrder.id == seller_order_id).with_for_update()
        )
        seller_order = result.scalar_one_or_none()
        if not seller_order:
            raise NotFoundError(f"SellerOrder {seller_order_id} not found")

        if await self.comm_repo.exists_for_seller_order(seller_order_id):
            return
        if seller_order.status.value != "delivered":
            raise BusinessRuleError("Only delivered orders can be settled")

        payment = await self.db.scalar(
            select(Payment).where(Payment.order_id == seller_order.order_id)
        )
        if not payment or payment.status != PaymentStatus.completed:
            raise BusinessRuleError("Funds must be collected before settling earnings")

        from app.services.platform_settings import get_platform_settings
        policy = await get_platform_settings(self.db)
        rate   = Decimal(str(policy.commission_rate))

        # ── Edge case: subtract refunds that arrived before settlement ──────────
        # In the normal flow this is 0; the query is cheap in the happy path.
        pre_confirmed = await self.db.scalar(
            select(func.coalesce(func.sum(Refund.amount), 0)).where(
                Refund.payment_id == payment.id,
                Refund.processed_at.is_not(None),
            )
        ) or Decimal("0")

        if pre_confirmed > Decimal("0"):
            # For multi-brand orders, prorate this seller's share of the refund by
            # their share of the total settled subtotals on the order.
            from app.models.order import SellerOrder as SO
            seller_subtotals = (
                await self.db.scalars(
                    select(SO.subtotal).where(SO.order_id == seller_order.order_id)
                )
            ).all()
            order_subtotal = sum(seller_subtotals, Decimal("0"))
            if order_subtotal > Decimal("0") and seller_order.subtotal < order_subtotal:
                # Multi-brand: prorate this seller's share.
                seller_share  = (seller_order.subtotal / order_subtotal).quantize(
                    Decimal("0.0001"), rounding=ROUND_HALF_UP
                )
                pre_confirmed = (pre_confirmed * seller_share).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )
            # Single-brand: apply full refund amount.

        gross_amount      = max(seller_order.subtotal - pre_confirmed, Decimal("0"))
        commission_amount = (gross_amount * rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        seller_amount     = gross_amount - commission_amount

        await self.comm_repo.create(
            seller_order_id   = seller_order_id,
            seller_id         = seller_order.seller_id,
            gross_amount      = gross_amount,
            commission_rate   = rate,
            commission_amount = commission_amount,
            seller_amount     = seller_amount,
        )

        if seller_amount > Decimal("0"):
            wallet = await self.wallet_repo.get_by_seller_id(seller_order.seller_id)
            if not wallet:
                raise NotFoundError("Seller wallet not found")

            await self.wallet_repo.credit_pending(seller_order.seller_id, seller_amount)
            await self.wallet_repo.charge_commission(seller_order.seller_id, commission_amount)

            updated = await self.db.scalar(
                select(SellerWallet)
                .where(SellerWallet.seller_id == seller_order.seller_id)
                .execution_options(populate_existing=True)
            )
            balance_after = updated.pending_balance

            note = (
                f"Commission settled: PKR {gross_amount:,.2f} × {rate * 100}%"
                f" = PKR {commission_amount:,.2f} WearHowZ,"
                f" PKR {seller_amount:,.2f} seller"
            )
            if pre_confirmed > Decimal("0"):
                note += f" (adjusted PKR {pre_confirmed:,.2f} pre-confirmed refund)"

            await self.tx_repo.create(
                seller_id       = seller_order.seller_id,
                type            = WalletTxType.credit_commission,
                amount          = seller_amount,
                balance_after   = balance_after,
                reference       = str(seller_order_id),
                seller_order_id = seller_order_id,
                note            = note,
            )

        if commit:
            await self.db.commit()
        else:
            await self.db.flush()

    # ── Refund reversal ─────────────────────────────────────────────────────────

    async def reverse_for_refund(
        self,
        refund_id: UUID,
        *,
        seller_order_id: UUID | None = None,
        order_id: UUID | None = None,
        refund_amount: Decimal,
        commit: bool = True,
    ) -> None:
        """
        Reverse the seller's wallet earnings proportionally when a customer refund
        is confirmed by an admin.

        Pass seller_order_id for return-linked refunds (single seller).
        Pass order_id for direct payment refunds (splits across all settled sellers).

        Guarantees:
        - Idempotent: safe to call any number of times for the same refund_id.
        - Best effort: if the seller has already withdrawn their balance, the wallet
          floors at zero; the transaction is still logged for reconciliation and the
          platform absorbs the shortfall.
        - No-op if no CommissionLedger exists yet (settle() will handle it via the
          pre-confirmed refund check above).
        """
        if seller_order_id is not None:
            await self._reverse_one(
                refund_id=refund_id,
                seller_order_id=seller_order_id,
                refund_amount=refund_amount,
            )
        elif order_id is not None:
            await self._reverse_across_order(
                refund_id=refund_id,
                order_id=order_id,
                refund_amount=refund_amount,
            )

        if commit:
            await self.db.commit()
        else:
            await self.db.flush()

    async def _reverse_one(
        self,
        refund_id: UUID,
        seller_order_id: UUID,
        refund_amount: Decimal,
    ) -> None:
        """Reverse earnings for one seller_order (return-linked refund)."""
        ref = f"return-refund:{refund_id}"
        if await self._already_reversed(ref, seller_order_id):
            return

        ledger = await self.db.scalar(
            select(CommissionLedger)
            .where(CommissionLedger.seller_order_id == seller_order_id)
            .with_for_update()
        )
        if not ledger or ledger.gross_amount == Decimal("0"):
            # Commission not yet settled or order was fully refunded at settle time.
            # settle() will use the reduced gross when it eventually runs.
            return

        debit = self._prorate(refund_amount, ledger.gross_amount, ledger.seller_amount)
        await self._apply_debit(
            seller_id=ledger.seller_id,
            debit=debit,
            reference=ref,
            seller_order_id=seller_order_id,
            released=ledger.released_at is not None,
            note=(
                f"Return refund reversal: PKR {refund_amount:,.2f}"
                f" of PKR {ledger.gross_amount:,.2f}"
                f" → seller debit PKR {debit:,.2f}"
            ),
        )

    async def _reverse_across_order(
        self,
        refund_id: UUID,
        order_id: UUID,
        refund_amount: Decimal,
    ) -> None:
        """
        Split a direct (non-return) refund proportionally across all settled
        seller_orders for an order.  Each seller's share is weighted by their
        subtotal against the sum of all seller subtotals.
        """
        from app.models.order import SellerOrder as SO

        seller_orders = (
            await self.db.execute(select(SO).where(SO.order_id == order_id))
        ).scalars().all()

        total_subtotal = sum((so.subtotal for so in seller_orders), Decimal("0"))
        if total_subtotal == Decimal("0"):
            return

        for so in seller_orders:
            ref = f"return-refund:{refund_id}:{so.id}"
            if await self._already_reversed(ref, so.id):
                continue

            ledger = await self.db.scalar(
                select(CommissionLedger)
                .where(CommissionLedger.seller_order_id == so.id)
                .with_for_update()
            )
            if not ledger or ledger.gross_amount == Decimal("0"):
                continue

            seller_share        = (so.subtotal / total_subtotal).quantize(
                Decimal("0.0001"), rounding=ROUND_HALF_UP
            )
            proportional_refund = (refund_amount * seller_share).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            if proportional_refund == Decimal("0"):
                continue

            debit = self._prorate(proportional_refund, ledger.gross_amount, ledger.seller_amount)
            await self._apply_debit(
                seller_id=ledger.seller_id,
                debit=debit,
                reference=ref,
                seller_order_id=so.id,
                released=ledger.released_at is not None,
                note=(
                    f"Direct refund allocation: PKR {proportional_refund:,.2f}"
                    f" of PKR {ledger.gross_amount:,.2f}"
                    f" → seller debit PKR {debit:,.2f}"
                ),
            )

    # ── Private helpers ─────────────────────────────────────────────────────────

    async def _already_reversed(self, reference: str, seller_order_id: UUID) -> bool:
        """True if a debit_adjustment WalletTransaction for this reference already exists."""
        return (
            await self.db.scalar(
                select(WalletTransaction.id).where(
                    WalletTransaction.reference    == reference,
                    WalletTransaction.seller_order_id == seller_order_id,
                    WalletTransaction.type         == WalletTxType.debit_adjustment,
                )
            )
        ) is not None

    @staticmethod
    def _prorate(
        refund_amount: Decimal,
        gross_amount: Decimal,
        target_amount: Decimal,
    ) -> Decimal:
        """
        Return target_amount × (refund_amount / gross_amount), capped at target_amount.
        Represents the seller's proportional share of the loss.
        """
        ratio = (refund_amount / gross_amount).quantize(
            Decimal("0.0001"), rounding=ROUND_HALF_UP
        )
        return min(
            (target_amount * ratio).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            target_amount,
        )

    async def _apply_debit(
        self,
        seller_id: UUID,
        debit: Decimal,
        reference: str,
        seller_order_id: UUID,
        released: bool,
        note: str,
    ) -> None:
        """
        Debit the seller wallet, best effort.

        Strategy:
        - If commission not yet released (hold period active): debit pending_balance first,
          then spill over to available_balance if pending is insufficient.
        - If commission already released to available: debit available_balance only.
        - In both cases the actual debit is floored at the available balance — the
          platform absorbs any shortfall (seller already withdrew).  The WalletTransaction
          is always logged at the full intended debit for reconciliation.
        """
        wallet = await self.db.scalar(
            select(SellerWallet)
            .where(SellerWallet.seller_id == seller_id)
            .with_for_update()
        )
        if not wallet:
            return

        if not released:
            # Funds still in hold: take from pending first, spill to available.
            from_pending   = min(debit, wallet.pending_balance)
            from_available = min(debit - from_pending, wallet.available_balance)
        else:
            # Funds released: only available_balance is in scope.
            from_pending   = Decimal("0")
            from_available = min(debit, wallet.available_balance)

        values: dict = {}
        if from_pending > Decimal("0"):
            values["pending_balance"] = SellerWallet.pending_balance - from_pending
        if from_available > Decimal("0"):
            values["available_balance"] = SellerWallet.available_balance - from_available
        if values:
            await self.db.execute(
                update(SellerWallet)
                .where(SellerWallet.seller_id == seller_id)
                .values(**values)
            )
        await self.db.flush()

        # Compute balance_after from known deltas — avoids a stale ORM cache read.
        balance_after = (
            (wallet.pending_balance   - from_pending)
            + (wallet.available_balance - from_available)
        )

        await self.tx_repo.create(
            seller_id       = seller_id,
            type            = WalletTxType.debit_adjustment,
            amount          = debit,          # intended amount, for audit
            balance_after   = balance_after,
            reference       = reference,
            seller_order_id = seller_order_id,
            note            = note,
        )

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
            pass  # Non-critical; worker polls committed ledger entries.