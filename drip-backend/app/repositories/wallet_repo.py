"""repositories / wallet repo.

Database operations used by services within their transaction boundaries.
"""

from __future__ import annotations

from uuid import UUID
from typing import Optional, Sequence
from datetime import datetime

from sqlalchemy import select, update, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.wallet import CommissionLedger, Payout, PayoutStatus, WalletTransaction, WalletTxType


class CommissionRepository:
    def __init__(self, db: AsyncSession) -> None:
        """Bind CommissionRepository to its injected dependencies for subsequent
        operations.
        """
        self.db = db

    async def create(self, **kwargs) -> CommissionLedger:
        """Insert a commission ledger entry and return it within the caller's transaction."""
        entry = CommissionLedger(**kwargs)
        self.db.add(entry)
        await self.db.flush()
        return entry

    async def exists_for_seller_order(self, seller_order_id: UUID) -> bool:
        """Check for an existing commission ledger entry for this seller order."""
        result = await self.db.execute(
            select(CommissionLedger.id).where(
                CommissionLedger.seller_order_id == seller_order_id
            )
        )
        return result.scalar_one_or_none() is not None

    async def list_by_seller(
        self,
        seller_id: UUID,
        date_from: Optional[str] = None,
        date_to:   Optional[str] = None,
        page:      int = 1,
        per_page:  int = 25,
    ) -> tuple[Sequence[CommissionLedger], int, dict]:
        """Query commission ledger entry records for by seller reads using the caller's
        session.
        """
        q = select(CommissionLedger).where(CommissionLedger.seller_id == seller_id)

        count_q = select(func.count()).select_from(q.subquery())
        total   = (await self.db.execute(count_q)).scalar_one()

        q = q.order_by(desc(CommissionLedger.settled_at)).offset((page - 1) * per_page).limit(per_page)
        result = await self.db.execute(q)
        rows   = result.scalars().all()

        # Summary
        summary_q = select(
            func.coalesce(func.sum(CommissionLedger.net_gross_amount), 0),
            func.coalesce(func.sum(CommissionLedger.net_commission_amount), 0),
            func.coalesce(func.sum(CommissionLedger.net_seller_amount), 0),
            func.coalesce(func.sum(CommissionLedger.gross_amount), 0),
            func.coalesce(func.sum(CommissionLedger.commission_amount), 0),
            func.coalesce(func.sum(CommissionLedger.seller_amount), 0),
            func.coalesce(func.sum(CommissionLedger.refunded_gross_amount), 0),
            func.coalesce(func.sum(CommissionLedger.reversed_commission_amount), 0),
            func.coalesce(func.sum(CommissionLedger.reversed_seller_amount), 0),
            func.coalesce(func.sum(CommissionLedger.recovered_seller_amount), 0),
            func.coalesce(func.sum(CommissionLedger.settlement_offset_amount), 0),
            func.coalesce(func.sum(CommissionLedger.platform_shortfall_amount), 0),
        ).where(CommissionLedger.seller_id == seller_id)
        sums = (await self.db.execute(summary_q)).one()
        summary = {
            "total_gross":      sums[0],
            "total_commission": sums[1],
            "total_net":        sums[2],
            "original_gross": sums[3],
            "original_commission": sums[4],
            "original_net": sums[5],
            "total_refunded_gross": sums[6],
            "total_reversed_commission": sums[7],
            "total_reversed_seller": sums[8],
            "total_recovered_seller": sums[9],
            "total_settlement_offset": sums[10],
            "total_platform_shortfall": sums[11],
        }

        return rows, total, summary


class WalletTransactionRepository:
    def __init__(self, db: AsyncSession) -> None:
        """Bind WalletTransactionRepository to its injected dependencies for subsequent
        operations.
        """
        self.db = db

    async def create(self, **kwargs) -> WalletTransaction:
        """Insert a wallet transaction and return it within the caller's transaction."""
        tx = WalletTransaction(**kwargs)
        self.db.add(tx)
        await self.db.flush()
        return tx

    async def list_by_seller(
        self,
        seller_id: UUID,
        tx_type:   Optional[str] = None,
        page:      int = 1,
        per_page:  int = 25,
    ) -> tuple[Sequence[WalletTransaction], int]:
        """Query wallet transaction records for by seller reads using the caller's session."""
        q = select(WalletTransaction).where(WalletTransaction.seller_id == seller_id)
        if tx_type:
            q = q.where(WalletTransaction.type == WalletTxType(tx_type))

        count_q = select(func.count()).select_from(q.subquery())
        total   = (await self.db.execute(count_q)).scalar_one()

        q = q.order_by(desc(WalletTransaction.created_at), desc(WalletTransaction.id)).offset((page - 1) * per_page).limit(per_page)
        result = await self.db.execute(q)
        return result.scalars().all(), total


class PayoutRepository:
    def __init__(self, db: AsyncSession) -> None:
        """Bind PayoutRepository to its injected dependencies for subsequent operations."""
        self.db = db

    async def create(self, **kwargs) -> Payout:
        """Insert a payout and return it within the caller's transaction."""
        payout = Payout(**kwargs)
        self.db.add(payout)
        await self.db.flush()
        await self.db.refresh(payout)
        return payout

    async def get_by_id(self, payout_id: UUID, *, for_update: bool = False) -> Optional[Payout]:
        """Look up a payout by id; return None when absent."""
        query = select(Payout).where(Payout.id == payout_id)
        if for_update:
            query = query.with_for_update().execution_options(populate_existing=True)
        result = await self.db.execute(
            query
        )
        return result.scalar_one_or_none()

    async def list_by_seller(
        self,
        seller_id: UUID,
        status:    Optional[str] = None,
        page:      int = 1,
        per_page:  int = 25,
    ) -> tuple[Sequence[Payout], int]:
        """Query payout records for by seller reads using the caller's session."""
        q = select(Payout).where(Payout.seller_id == seller_id)
        if status:
            q = q.where(Payout.status == PayoutStatus(status))

        count_q = select(func.count()).select_from(q.subquery())
        total   = (await self.db.execute(count_q)).scalar_one()

        q = q.order_by(desc(Payout.requested_at), desc(Payout.id)).offset((page - 1) * per_page).limit(per_page)
        result = await self.db.execute(q)
        return result.scalars().all(), total

    async def list_admin(
        self,
        status:   Optional[str] = None,
        page:     int = 1,
        per_page: int = 25,
    ) -> tuple[Sequence[Payout], int]:
        """Query payout records for admin reads using the caller's session."""
        q = select(Payout)
        if status:
            q = q.where(Payout.status == PayoutStatus(status))

        count_q = select(func.count()).select_from(q.subquery())
        total   = (await self.db.execute(count_q)).scalar_one()

        q = q.order_by(desc(Payout.requested_at), desc(Payout.id)).offset((page - 1) * per_page).limit(per_page)
        result = await self.db.execute(q)
        return result.scalars().all(), total

    async def update_status(
        self,
        payout_id:   UUID,
        status:      PayoutStatus,
        approved_by: Optional[UUID] = None,
        admin_note:  Optional[str] = None,
    ) -> None:
        """Apply the payout status change within the caller's transaction."""
        values: dict = {"status": status}
        if approved_by:
            values["approved_by"] = approved_by
        if admin_note:
            values["admin_note"] = admin_note
        if status == PayoutStatus.completed:
            values["completed_at"] = datetime.utcnow()
        await self.db.execute(
            update(Payout).where(Payout.id == payout_id).values(**values)
        )
