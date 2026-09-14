from __future__ import annotations

from decimal import Decimal
from uuid import UUID
from typing import Optional, Sequence
from datetime import datetime

from sqlalchemy import select, update, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.wallet import CommissionLedger, Payout, PayoutStatus, WalletTransaction, WalletTxType
from app.models.seller import SellerWallet


class CommissionRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, **kwargs) -> CommissionLedger:
        entry = CommissionLedger(**kwargs)
        self.db.add(entry)
        await self.db.flush()
        return entry

    async def exists_for_seller_order(self, seller_order_id: UUID) -> bool:
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
        q = select(CommissionLedger).where(CommissionLedger.seller_id == seller_id)

        count_q = select(func.count()).select_from(q.subquery())
        total   = (await self.db.execute(count_q)).scalar_one()

        q = q.order_by(desc(CommissionLedger.settled_at)).offset((page - 1) * per_page).limit(per_page)
        result = await self.db.execute(q)
        rows   = result.scalars().all()

        # Summary
        summary_q = select(
            func.coalesce(func.sum(CommissionLedger.gross_amount),      0),
            func.coalesce(func.sum(CommissionLedger.commission_amount), 0),
            func.coalesce(func.sum(CommissionLedger.seller_amount),     0),
        ).where(CommissionLedger.seller_id == seller_id)
        sums = (await self.db.execute(summary_q)).one()
        summary = {
            "total_gross":      int(sums[0]),
            "total_commission": int(sums[1]),
            "total_net":        int(sums[2]),
        }

        return rows, total, summary


class WalletTransactionRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, **kwargs) -> WalletTransaction:
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
        q = select(WalletTransaction).where(WalletTransaction.seller_id == seller_id)
        if tx_type:
            q = q.where(WalletTransaction.type == WalletTxType(tx_type))

        count_q = select(func.count()).select_from(q.subquery())
        total   = (await self.db.execute(count_q)).scalar_one()

        q = q.order_by(desc(WalletTransaction.created_at)).offset((page - 1) * per_page).limit(per_page)
        result = await self.db.execute(q)
        return result.scalars().all(), total


class PayoutRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, **kwargs) -> Payout:
        payout = Payout(**kwargs)
        self.db.add(payout)
        await self.db.flush()
        await self.db.refresh(payout)
        return payout

    async def get_by_id(self, payout_id: UUID) -> Optional[Payout]:
        result = await self.db.execute(
            select(Payout).where(Payout.id == payout_id)
        )
        return result.scalar_one_or_none()

    async def list_by_seller(
        self,
        seller_id: UUID,
        status:    Optional[str] = None,
        page:      int = 1,
        per_page:  int = 25,
    ) -> tuple[Sequence[Payout], int]:
        q = select(Payout).where(Payout.seller_id == seller_id)
        if status:
            q = q.where(Payout.status == PayoutStatus(status))

        count_q = select(func.count()).select_from(q.subquery())
        total   = (await self.db.execute(count_q)).scalar_one()

        q = q.order_by(desc(Payout.requested_at)).offset((page - 1) * per_page).limit(per_page)
        result = await self.db.execute(q)
        return result.scalars().all(), total

    async def list_admin(
        self,
        status:   Optional[str] = None,
        page:     int = 1,
        per_page: int = 25,
    ) -> tuple[Sequence[Payout], int]:
        q = select(Payout)
        if status:
            q = q.where(Payout.status == PayoutStatus(status))

        count_q = select(func.count()).select_from(q.subquery())
        total   = (await self.db.execute(count_q)).scalar_one()

        q = q.order_by(desc(Payout.requested_at)).offset((page - 1) * per_page).limit(per_page)
        result = await self.db.execute(q)
        return result.scalars().all(), total

    async def update_status(
        self,
        payout_id:   UUID,
        status:      PayoutStatus,
        approved_by: Optional[UUID] = None,
        admin_note:  Optional[str] = None,
    ) -> None:
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