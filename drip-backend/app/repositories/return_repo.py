from __future__ import annotations

from datetime import datetime
from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy import desc, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.order import SellerOrder
from app.models.return_ import (
    Dispute,
    DisputeMessage,
    DisputeStatus,
    Return,
    ReturnItem,
    ReturnStatus,
)


class ReturnRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, **kwargs) -> Return:
        r = Return(**kwargs)
        self.db.add(r)
        await self.db.flush()
        await self.db.refresh(r)
        return r

    async def add_item(self, **kwargs) -> ReturnItem:
        item = ReturnItem(**kwargs)
        self.db.add(item)
        await self.db.flush()
        return item

    async def get_by_id(
        self,
        return_id: UUID,
        user_id: Optional[UUID] = None,
        *,
        for_update: bool = False,
    ) -> Optional[Return]:
        q = select(Return).options(
            selectinload(Return.items),
            selectinload(Return.dispute).selectinload(Dispute.messages),
        ).where(Return.id == return_id)
        if user_id:
            q = q.where(Return.user_id == user_id)
        if for_update:
            q = q.with_for_update()
        result = await self.db.execute(q.execution_options(populate_existing=True))
        return result.scalar_one_or_none()

    async def list_by_user(
        self, user_id: UUID, page: int = 1, per_page: int = 10
    ) -> tuple[Sequence[Return], int]:
        q = select(Return).options(selectinload(Return.items)).where(Return.user_id == user_id)

        count_q = select(func.count()).select_from(q.subquery())
        total   = (await self.db.execute(count_q)).scalar_one()

        q = q.order_by(desc(Return.requested_at)).offset((page - 1) * per_page).limit(per_page)
        result = await self.db.execute(q)
        return result.scalars().all(), total

    async def list_admin(
        self, status: Optional[str] = None, page: int = 1, per_page: int = 25
    ) -> tuple[Sequence[Return], int]:
        q = select(Return).options(selectinload(Return.items))
        if status:
            q = q.where(Return.status == ReturnStatus(status))

        count_q = select(func.count()).select_from(q.subquery())
        total   = (await self.db.execute(count_q)).scalar_one()

        q = q.order_by(desc(Return.requested_at)).offset((page - 1) * per_page).limit(per_page)
        result = await self.db.execute(q)
        return result.scalars().all(), total

    async def get_by_seller(
        self, return_id: UUID, seller_id: UUID, *, for_update: bool = False
    ) -> Optional[Return]:
        query = (
            select(Return)
            .join(SellerOrder, SellerOrder.id == Return.seller_order_id)
            .options(
                selectinload(Return.items),
                selectinload(Return.dispute).selectinload(Dispute.messages),
            )
            .where(Return.id == return_id, SellerOrder.seller_id == seller_id)
            .execution_options(populate_existing=True)
        )
        if for_update:
            query = query.with_for_update(of=Return)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def list_seller(
        self,
        seller_id: UUID,
        status: Optional[str] = None,
        page: int = 1,
        per_page: int = 25,
    ) -> tuple[Sequence[Return], int]:
        q = (
            select(Return)
            .join(SellerOrder, SellerOrder.id == Return.seller_order_id)
            .options(selectinload(Return.items))
            .where(SellerOrder.seller_id == seller_id)
        )
        if status:
            q = q.where(Return.status == ReturnStatus(status))

        total = (await self.db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
        rows = await self.db.execute(
            q.order_by(desc(Return.requested_at))
            .offset((page - 1) * per_page)
            .limit(per_page)
        )
        return rows.scalars().all(), total

    async def update_status(
        self,
        return_id:   UUID,
        status:      ReturnStatus,
        notes:       Optional[str] = None,
        resolved_at: Optional[datetime] = None,
    ) -> None:
        values: dict = {"status": status}
        if notes:
            values["notes"] = notes
        if resolved_at:
            values["resolved_at"] = resolved_at
        await self.db.execute(
            update(Return).where(Return.id == return_id).values(**values)
        )


class DisputeRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, **kwargs) -> Dispute:
        d = Dispute(**kwargs)
        self.db.add(d)
        await self.db.flush()
        await self.db.refresh(d)
        return d

    async def get_by_id(
        self, dispute_id: UUID, *, for_update: bool = False
    ) -> Optional[Dispute]:
        query = (
            select(Dispute)
            .options(selectinload(Dispute.messages))
            .where(Dispute.id == dispute_id)
        )
        if for_update:
            query = query.with_for_update()
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_by_return_id(
        self, return_id: UUID, *, for_update: bool = False
    ) -> Optional[Dispute]:
        query = (
            select(Dispute)
            .options(selectinload(Dispute.messages))
            .where(Dispute.return_id == return_id)
        )
        if for_update:
            query = query.with_for_update()
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def add_message(self, **kwargs) -> DisputeMessage:
        msg = DisputeMessage(**kwargs)
        self.db.add(msg)
        await self.db.flush()
        return msg

    async def list_admin(
        self, status: Optional[str] = None, page: int = 1, per_page: int = 25
    ) -> tuple[Sequence[Dispute], int]:
        q = select(Dispute).options(selectinload(Dispute.messages))
        if status:
            q = q.where(Dispute.status == DisputeStatus(status))

        count_q = select(func.count()).select_from(q.subquery())
        total   = (await self.db.execute(count_q)).scalar_one()

        q = q.order_by(desc(Dispute.created_at)).offset((page - 1) * per_page).limit(per_page)
        result = await self.db.execute(q)
        return result.scalars().all(), total

    async def resolve(
        self,
        dispute_id:      UUID,
        status:          DisputeStatus,
        resolution_note: str,
        resolved_by:     UUID,
    ) -> None:
        await self.db.execute(
            update(Dispute)
            .where(Dispute.id == dispute_id)
            .values(
                status          = status,
                resolution_note = resolution_note,
                resolved_by     = resolved_by,
                resolved_at     = datetime.utcnow(),
            )
        )
