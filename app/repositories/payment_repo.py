from __future__ import annotations

from decimal import Decimal
from uuid import UUID
from typing import Optional, Sequence
from datetime import datetime

from sqlalchemy import select, update, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.payment import Payment, PaymentStatus, PaymentCallback, Refund
from app.models.order import Order


class PaymentRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, **kwargs) -> Payment:
        payment = Payment(**kwargs)
        self.db.add(payment)
        await self.db.flush()
        await self.db.refresh(payment)
        return payment

    async def get_by_id(self, payment_id: UUID) -> Optional[Payment]:
        result = await self.db.execute(
            select(Payment)
            .options(selectinload(Payment.refunds))
            .where(Payment.id == payment_id)
        )
        return result.scalar_one_or_none()

    async def get_by_order_id(self, order_id: UUID) -> Optional[Payment]:
        result = await self.db.execute(
            select(Payment).where(Payment.order_id == order_id)
        )
        return result.scalar_one_or_none()

    async def get_by_gateway_reference(self, ref: str) -> Optional[Payment]:
        result = await self.db.execute(
            select(Payment).where(Payment.gateway_reference == ref)
        )
        return result.scalar_one_or_none()

    async def update_status(
        self,
        payment_id: UUID,
        status: PaymentStatus,
        *,
        gateway_reference: Optional[str] = None,
        gateway_payload: Optional[dict] = None,
        failure_reason: Optional[str] = None,
        paid_at: Optional[datetime] = None,
    ) -> None:
        values: dict = {"status": status}
        if gateway_reference:
            values["gateway_reference"] = gateway_reference
        if gateway_payload:
            values["gateway_payload"] = gateway_payload
        if failure_reason:
            values["failure_reason"] = failure_reason
        if paid_at:
            values["paid_at"] = paid_at
        await self.db.execute(
            update(Payment).where(Payment.id == payment_id).values(**values)
        )

    async def log_callback(
        self,
        gateway: str,
        raw_payload: dict,
        payment_id: Optional[UUID] = None,
        is_verified: bool = False,
    ) -> PaymentCallback:
        cb = PaymentCallback(
            gateway=gateway,
            raw_payload=raw_payload,
            payment_id=payment_id,
            is_verified=is_verified,
        )
        self.db.add(cb)
        await self.db.flush()
        return cb

    async def create_refund(self, **kwargs) -> Refund:
        refund = Refund(**kwargs)
        self.db.add(refund)
        await self.db.flush()
        await self.db.refresh(refund)
        return refund

    async def get_total_refunded(self, payment_id: UUID) -> Decimal:
        result = await self.db.execute(
            select(func.coalesce(func.sum(Refund.amount), 0))
            .where(Refund.payment_id == payment_id)
        )
        return result.scalar_one()

    async def list_admin(
        self,
        status: Optional[str] = None,
        method: Optional[str] = None,
        page: int = 1,
        per_page: int = 25,
    ) -> tuple[Sequence[Payment], int]:
        q = select(Payment)
        if status:
            q = q.where(Payment.status == PaymentStatus(status))
        if method:
            q = q.where(Payment.method == method)

        count_q = select(func.count()).select_from(q.subquery())
        total   = (await self.db.execute(count_q)).scalar_one()

        q = q.order_by(desc(Payment.created_at)).offset((page - 1) * per_page).limit(per_page)
        result = await self.db.execute(q)
        return result.scalars().all(), total