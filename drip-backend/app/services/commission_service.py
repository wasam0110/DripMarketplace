"""Commission settlement and refund reversal accounting."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID

from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessRuleError, NotFoundError
from app.models.seller import SellerWallet
from app.models.wallet import (
    CommissionLedger,
    RefundAccounting,
    RefundAllocation,
    WalletTransaction,
    WalletTxType,
)
from app.repositories.wallet_repo import CommissionRepository, WalletTransactionRepository
from app.repositories.seller_repo import WalletRepository

# Unit-test default only — runtime always reads from platform_settings.
COMMISSION_RATE  = Decimal("0.15")
WALLET_HOLD_DAYS = 3


class CommissionService:
    def __init__(self, db: AsyncSession) -> None:
        """Bind CommissionService to its injected dependencies for subsequent operations."""
        self.db          = db
        self.comm_repo   = CommissionRepository(db)
        self.tx_repo     = WalletTransactionRepository(db)
        self.wallet_repo = WalletRepository(db)

    # ── Settlement ─────────────────────────────────────────────────────────────

    async def settle(self, seller_order_id: UUID, *, commit: bool = True) -> None:
        """
        Credit the seller's pending_balance when a SellerOrder is delivered and paid.

        Idempotent — skips silently if this seller_order already has a ledger entry.

        Refund allocations confirmed before settlement are applied as explicit
        offsets against this seller's ledger before any wallet credit is created.
        """
        from app.models.order import SellerOrder
        from app.models.payment import Payment, PaymentStatus

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

        gross_amount = Decimal(seller_order.subtotal)
        commission_amount = self._money(gross_amount * rate)
        seller_amount = gross_amount - commission_amount

        ledger = await self.comm_repo.create(
            seller_order_id   = seller_order_id,
            seller_id         = seller_order.seller_id,
            gross_amount      = gross_amount,
            commission_rate   = rate,
            commission_amount = commission_amount,
            seller_amount     = seller_amount,
        )

        pending_allocations = (
            await self.db.execute(
                select(RefundAllocation)
                .where(
                    RefundAllocation.seller_order_id == seller_order_id,
                    RefundAllocation.applied_at.is_(None),
                )
                .order_by(RefundAllocation.id)
                .with_for_update()
            )
        ).scalars().all()
        refund_ids: set[UUID] = set()
        for allocation in pending_allocations:
            await self._apply_allocation(
                allocation,
                ledger=ledger,
                settlement_offset=True,
            )
            refund_ids.add(allocation.refund_id)

        net_seller = ledger.net_seller_amount
        net_commission = ledger.net_commission_amount

        if net_seller > Decimal("0"):
            wallet = await self.wallet_repo.get_by_seller_id(seller_order.seller_id)
            if not wallet:
                raise NotFoundError("Seller wallet not found")

            await self.wallet_repo.credit_pending(seller_order.seller_id, net_seller)
            await self.wallet_repo.charge_commission(seller_order.seller_id, net_commission)

            updated = await self.db.scalar(
                select(SellerWallet)
                .where(SellerWallet.seller_id == seller_order.seller_id)
                .execution_options(populate_existing=True)
            )
            balance_after = updated.pending_balance

            note = (
                f"Commission settled: PKR {ledger.net_gross_amount:,.2f} net"
                f" = PKR {net_commission:,.2f} WearHowZ,"
                f" PKR {net_seller:,.2f} seller"
            )
            if ledger.refunded_gross_amount > Decimal("0"):
                note += (
                    f" (PKR {ledger.refunded_gross_amount:,.2f}"
                    " pre-settlement refund allocation)"
                )

            await self.tx_repo.create(
                seller_id       = seller_order.seller_id,
                type            = WalletTxType.credit_commission,
                amount          = net_seller,
                balance_after   = balance_after,
                reference       = str(seller_order_id),
                seller_order_id = seller_order_id,
                note            = note,
            )

        for refund_id in refund_ids:
            await self._refresh_refund_accounting(refund_id)

        if commit:
            await self.db.commit()
        else:
            await self.db.flush()

    async def _create_refund_accounting(
        self,
        *,
        refund_id: UUID,
        seller_order_id: UUID | None,
        order_id: UUID | None,
        refund_amount: Decimal,
    ) -> RefundAccounting:
        """Persist one deterministic merchandise/shipping allocation for a refund."""
        from app.models.order import Order, SellerOrder
        from app.models.payment import Payment, Refund

        if seller_order_id is not None:
            seller_order = await self.db.scalar(
                select(SellerOrder)
                .where(SellerOrder.id == seller_order_id)
                .with_for_update()
            )
            if seller_order is None:
                raise NotFoundError("Seller order for refund allocation was not found")
            resolved_order_id = seller_order.order_id
            seller_orders = [seller_order]
        elif order_id is not None:
            resolved_order_id = order_id
            seller_orders = (
                await self.db.execute(
                    select(SellerOrder)
                    .where(SellerOrder.order_id == order_id)
                    .order_by(SellerOrder.id)
                    .with_for_update()
                )
            ).scalars().all()
        else:
            raise BusinessRuleError("A seller order or order is required for refund allocation")

        order = await self.db.get(Order, resolved_order_id)
        if order is None or not seller_orders:
            raise BusinessRuleError("Refund order has no seller allocation")

        unallocated_historical = await self.db.scalar(
            select(Refund.id)
            .join(Payment, Refund.payment_id == Payment.id)
            .where(
                Payment.order_id == resolved_order_id,
                Refund.id != refund_id,
                Refund.processed_at.is_not(None),
                ~select(RefundAccounting.refund_id)
                .where(RefundAccounting.refund_id == Refund.id)
                .exists(),
            )
            .limit(1)
        )
        if unallocated_historical is not None:
            raise BusinessRuleError(
                "Historical refunds on this order require reconciliation before another refund"
            )

        prior_rows = (
            await self.db.execute(
                select(
                    RefundAllocation.seller_order_id,
                    func.coalesce(func.sum(RefundAllocation.merchandise_amount), 0),
                )
                .where(
                    RefundAllocation.seller_order_id.in_([so.id for so in seller_orders])
                )
                .group_by(RefundAllocation.seller_order_id)
            )
        ).all()
        prior = {row[0]: Decimal(row[1]) for row in prior_rows}
        capacities = [
            (so, max(Decimal(so.subtotal) - prior.get(so.id, Decimal("0")), Decimal("0")))
            for so in seller_orders
        ]

        if seller_order_id is not None:
            merchandise_amount = refund_amount
            shipping_amount = Decimal("0")
            if merchandise_amount > capacities[0][1]:
                raise BusinessRuleError(
                    "Return refund exceeds this seller order's remaining merchandise value"
                )
            split = [(seller_orders[0], merchandise_amount)]
        else:
            merchandise_capacity = sum((capacity for _, capacity in capacities), Decimal("0"))
            merchandise_amount = min(refund_amount, merchandise_capacity)
            shipping_amount = refund_amount - merchandise_amount
            prior_shipping = await self.db.scalar(
                select(func.coalesce(func.sum(RefundAccounting.shipping_amount), 0))
                .join(Refund, RefundAccounting.refund_id == Refund.id)
                .join(Payment, Refund.payment_id == Payment.id)
                .where(Payment.order_id == resolved_order_id)
            ) or Decimal("0")
            if shipping_amount > max(Decimal(order.shipping_fee) - prior_shipping, Decimal("0")):
                raise BusinessRuleError("Refund exceeds remaining merchandise and shipping value")
            split = self._split_allocation(merchandise_amount, capacities)

        accounting = RefundAccounting(
            refund_id=refund_id,
            merchandise_amount=merchandise_amount,
            shipping_amount=shipping_amount,
            commission_reversal_amount=Decimal("0"),
            seller_reversal_amount=Decimal("0"),
            recovered_amount=Decimal("0"),
            settlement_offset_amount=Decimal("0"),
            platform_shortfall_amount=Decimal("0"),
            platform_funded_amount=shipping_amount,
        )
        self.db.add(accounting)
        for seller_order, amount in split:
            if amount <= Decimal("0"):
                continue
            self.db.add(
                RefundAllocation(
                    refund_id=refund_id,
                    seller_order_id=seller_order.id,
                    seller_id=seller_order.seller_id,
                    merchandise_amount=amount,
                    commission_reversal_amount=Decimal("0"),
                    seller_reversal_amount=Decimal("0"),
                    recovered_amount=Decimal("0"),
                    settlement_offset_amount=Decimal("0"),
                    platform_shortfall_amount=Decimal("0"),
                )
            )
        await self.db.flush()
        return accounting

    @classmethod
    def _split_allocation(cls, amount: Decimal, capacities: list[tuple[object, Decimal]]):
        """Split cents proportionally; the final eligible seller absorbs the residual."""
        eligible = [(seller_order, capacity) for seller_order, capacity in capacities if capacity > 0]
        if amount <= 0:
            return []
        if amount > sum((capacity for _, capacity in eligible), Decimal("0")):
            raise BusinessRuleError("Refund exceeds remaining merchandise value")

        result = []
        remaining_amount = amount
        remaining_capacity = sum((capacity for _, capacity in eligible), Decimal("0"))
        for index, (seller_order, capacity) in enumerate(eligible):
            if index == len(eligible) - 1:
                share = remaining_amount
            else:
                share = min(
                    capacity,
                    cls._money(remaining_amount * capacity / remaining_capacity),
                )
            if share > 0:
                result.append((seller_order, share))
                remaining_amount -= share
            remaining_capacity -= capacity
        if remaining_amount != Decimal("0"):
            raise BusinessRuleError("Refund allocation left an unreconciled rounding residual")
        return result

    async def _apply_allocation(
        self,
        allocation: RefundAllocation,
        *,
        ledger: CommissionLedger | None = None,
        settlement_offset: bool = False,
    ) -> bool:
        """Apply one allocation to its ledger and wallet exactly once."""
        if allocation.applied_at is not None:
            return True
        if ledger is None:
            ledger = await self.db.scalar(
                select(CommissionLedger)
                .where(CommissionLedger.seller_order_id == allocation.seller_order_id)
                .with_for_update()
            )
        if ledger is None:
            return False

        gross_remaining = ledger.net_gross_amount
        commission_remaining = ledger.net_commission_amount
        seller_remaining = ledger.net_seller_amount
        merchandise = Decimal(allocation.merchandise_amount)
        if merchandise > gross_remaining:
            raise BusinessRuleError("Refund allocation exceeds remaining ledger gross")

        commission_reversal = min(
            self._money(merchandise * Decimal(ledger.commission_rate)),
            commission_remaining,
        )
        seller_reversal = merchandise - commission_reversal
        if seller_reversal > seller_remaining:
            seller_reversal = seller_remaining
            commission_reversal = merchandise - seller_reversal
        if commission_reversal > commission_remaining:
            raise BusinessRuleError("Refund allocation exceeds remaining commission")

        if settlement_offset:
            recovered = Decimal("0")
            offset = seller_reversal
            shortfall = Decimal("0")
        else:
            from app.models.payment import Refund

            return_id = await self.db.scalar(
                select(Refund.return_id).where(Refund.id == allocation.refund_id)
            )
            reference = f"return-refund:{allocation.refund_id}"
            if return_id is None:
                reference += f":{allocation.seller_order_id}"
            recovered = await self._apply_debit(
                seller_id=ledger.seller_id,
                debit=seller_reversal,
                reference=reference,
                seller_order_id=allocation.seller_order_id,
                released=ledger.released_at is not None,
                note=(
                    f"Refund allocation: PKR {merchandise:,.2f} merchandise"
                    f" -> seller reversal PKR {seller_reversal:,.2f}"
                ),
            )
            offset = Decimal("0")
            shortfall = seller_reversal - recovered
            await self.db.execute(
                update(SellerWallet)
                .where(SellerWallet.seller_id == ledger.seller_id)
                .values(
                    total_earned=SellerWallet.total_earned - seller_reversal,
                    total_commission=(
                        SellerWallet.total_commission - commission_reversal
                    ),
                )
            )

        ledger.refunded_gross_amount += merchandise
        ledger.reversed_commission_amount += commission_reversal
        ledger.reversed_seller_amount += seller_reversal
        ledger.recovered_seller_amount += recovered
        ledger.settlement_offset_amount += offset
        ledger.platform_shortfall_amount += shortfall

        allocation.commission_rate = ledger.commission_rate
        allocation.commission_reversal_amount = commission_reversal
        allocation.seller_reversal_amount = seller_reversal
        allocation.recovered_amount = recovered
        allocation.settlement_offset_amount = offset
        allocation.platform_shortfall_amount = shortfall
        allocation.applied_at = datetime.now(UTC)
        await self.db.flush()
        return True

    async def _refresh_refund_accounting(self, refund_id: UUID) -> None:
        """Recalculate refund reconciliation totals from the seller allocation records."""
        accounting = await self.db.scalar(
            select(RefundAccounting)
            .where(RefundAccounting.refund_id == refund_id)
            .with_for_update()
        )
        if accounting is None:
            return
        allocations = (
            await self.db.execute(
                select(RefundAllocation).where(RefundAllocation.refund_id == refund_id)
            )
        ).scalars().all()
        accounting.commission_reversal_amount = sum(
            (row.commission_reversal_amount for row in allocations), Decimal("0")
        )
        accounting.seller_reversal_amount = sum(
            (row.seller_reversal_amount for row in allocations), Decimal("0")
        )
        accounting.recovered_amount = sum(
            (row.recovered_amount for row in allocations), Decimal("0")
        )
        accounting.settlement_offset_amount = sum(
            (row.settlement_offset_amount for row in allocations), Decimal("0")
        )
        accounting.platform_shortfall_amount = sum(
            (row.platform_shortfall_amount for row in allocations), Decimal("0")
        )
        accounting.platform_funded_amount = (
            accounting.shipping_amount
            + accounting.commission_reversal_amount
            + accounting.platform_shortfall_amount
        )
        accounting.reconciled_at = (
            datetime.now(UTC)
            if all(row.applied_at is not None for row in allocations)
            else None
        )
        await self.db.flush()

    @staticmethod
    def _money(value: Decimal) -> Decimal:
        """Quantize monetary calculations to PKR's two decimal places."""
        return Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    async def release_mature(self, *, now: datetime | None = None) -> int:
        """Release each mature ledger's net entitlement unless that seller is held."""
        from app.models.order import SellerOrder
        from app.models.payment import Payment, Refund
        from app.models.return_ import Dispute, DisputeStatus, Return, ReturnStatus
        from app.services.platform_settings import get_platform_settings

        now = now or datetime.now(UTC)
        policy = await get_platform_settings(self.db)
        rows = (
            await self.db.execute(
                select(CommissionLedger)
                .where(
                    CommissionLedger.released_at.is_(None),
                    CommissionLedger.settled_at
                    <= now - timedelta(days=policy.wallet_hold_days),
                )
                .order_by(CommissionLedger.settled_at, CommissionLedger.id)
                .with_for_update(skip_locked=True)
            )
        ).scalars().all()
        released = 0
        for ledger in rows:
            seller_order = await self.db.get(SellerOrder, ledger.seller_order_id)
            if seller_order is None or seller_order.status.value != "delivered":
                continue

            active_hold = await self.db.scalar(
                select(Return.id)
                .outerjoin(Dispute, Dispute.return_id == Return.id)
                .where(
                    Return.seller_order_id == ledger.seller_order_id,
                    or_(
                        Return.status.in_(
                            [
                                ReturnStatus.requested,
                                ReturnStatus.approved,
                                ReturnStatus.received,
                            ]
                        ),
                        Dispute.status.in_(
                            [
                                DisputeStatus.open,
                                DisputeStatus.under_review,
                                DisputeStatus.resolved_customer,
                            ]
                        ),
                    ),
                )
                .limit(1)
            )
            if active_hold is not None:
                continue

            legacy_refund = await self.db.scalar(
                select(Refund.id)
                .join(Payment, Refund.payment_id == Payment.id)
                .where(
                    Payment.order_id == seller_order.order_id,
                    Refund.processed_at.is_not(None),
                    ~select(RefundAccounting.refund_id)
                    .where(RefundAccounting.refund_id == Refund.id)
                    .exists(),
                )
                .limit(1)
            )
            if legacy_refund is not None:
                continue

            amount = ledger.net_seller_amount
            wallet = await self.db.scalar(
                select(SellerWallet)
                .where(SellerWallet.seller_id == ledger.seller_id)
                .with_for_update()
            )
            if wallet is None or wallet.pending_balance < amount:
                continue
            if amount > Decimal("0"):
                wallet.pending_balance -= amount
                wallet.available_balance += amount
                await self.tx_repo.create(
                    seller_id=ledger.seller_id,
                    type=WalletTxType.credit_adjustment,
                    amount=amount,
                    balance_after=wallet.pending_balance + wallet.available_balance,
                    reference=str(ledger.id),
                    seller_order_id=ledger.seller_order_id,
                    note="Settlement hold released",
                )
            ledger.released_at = now
            released += 1
        await self.db.commit()
        return released

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
        accounting = await self.db.scalar(
            select(RefundAccounting)
            .where(RefundAccounting.refund_id == refund_id)
            .with_for_update()
        )
        if accounting is None:
            accounting = await self._create_refund_accounting(
                refund_id=refund_id,
                seller_order_id=seller_order_id,
                order_id=order_id,
                refund_amount=self._money(refund_amount),
            )

        allocations = (
            await self.db.execute(
                select(RefundAllocation)
                .where(
                    RefundAllocation.refund_id == refund_id,
                    RefundAllocation.applied_at.is_(None),
                )
                .order_by(RefundAllocation.id)
                .with_for_update()
            )
        ).scalars().all()
        for allocation in allocations:
            await self._apply_allocation(allocation)
        await self._refresh_refund_accounting(refund_id)

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
    ) -> Decimal:
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
            return Decimal("0")

        # SQLAlchemy may synchronize the loaded wallet when the UPDATE below is
        # executed. Capture the pre-update values so balance_after is independent
        # of that synchronization behavior.
        pending_before = Decimal(wallet.pending_balance)
        available_before = Decimal(wallet.available_balance)

        if not released:
            # Funds still in hold: take from pending first, spill to available.
            from_pending   = min(debit, pending_before)
            from_available = min(debit - from_pending, available_before)
        else:
            # Funds released: only available_balance is in scope.
            from_pending   = Decimal("0")
            from_available = min(debit, available_before)

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

        # Record the combined post-transaction wallet balance from the captured
        # values, regardless of ORM identity-map synchronization.
        balance_after = (
            (pending_before - from_pending)
            + (available_before - from_available)
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
        return from_pending + from_available

    async def _enqueue_release(self, seller_id: UUID, amount: Decimal) -> None:
        """Schedule wallet release work; the periodic worker sweep provides recovery."""
        try:
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
