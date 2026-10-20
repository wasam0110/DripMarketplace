"""repositories / payment repo.

Database operations used by services within their transaction boundaries.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy import desc, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.models.payment import Payment, PaymentCallback, PaymentStatus, Refund
from app.models.wallet import RefundAccounting


class PaymentRepository:
    def __init__(self, db: AsyncSession) -> None:
        """Bind PaymentRepository to its injected dependencies for subsequent operations."""
        self.db = db

    async def create(self, **kwargs) -> Payment:
        """Insert a payment and return it within the caller's transaction."""
        payment = Payment(**kwargs)
        self.db.add(payment)
        await self.db.flush()
        await self.db.refresh(payment)
        return payment

    async def get_by_id(self, payment_id: UUID) -> Optional[Payment]:
        """Look up a payment by id; return None when absent."""
        result = await self.db.execute(
            select(Payment)
            .options(selectinload(Payment.refunds))
            .where(Payment.id == payment_id)
        )
        return result.scalar_one_or_none()

    async def get_by_order_id(self, order_id: UUID) -> Optional[Payment]:
        """Look up a payment by order id; return None when absent."""
        result = await self.db.execute(
            select(Payment).where(Payment.order_id == order_id)
        )
        return result.scalar_one_or_none()

    async def get_by_gateway_reference(self, ref: str) -> Optional[Payment]:
        """Look up a payment by gateway reference; return None when absent."""
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
        """Apply the payment status change within the caller's transaction."""
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
        """Persist the provider callback audit record for payment reconciliation."""
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
        """Persist a refund request within the caller's transaction."""
        refund = Refund(**kwargs)
        self.db.add(refund)
        await self.db.flush()
        await self.db.refresh(refund)
        return refund

    async def get_total_refunded(self, payment_id: UUID) -> Decimal:
        """Sum refund amounts according to the repository's refund-status filter."""
        result = await self.db.execute(
            select(func.coalesce(func.sum(Refund.amount), 0))
            .where(Refund.payment_id == payment_id)
        )
        return result.scalar_one()

    async def list_refunds_admin(
        self,
        status: Optional[str] = None,
        payment_id: Optional[UUID] = None,
        page: int = 1,
        per_page: int = 25,
    ) -> tuple[Sequence[Refund], int]:
        """Query payment records for refunds admin reads using the caller's session."""
        query = select(Refund).options(
            selectinload(Refund.payment).selectinload(Payment.order),
            joinedload(Refund.accounting).selectinload(RefundAccounting.allocations),
        )
        if status == "pending":
            query = query.where(Refund.processed_at.is_(None))
        elif status == "completed":
            query = query.where(Refund.processed_at.is_not(None))
        if payment_id:
            query = query.where(Refund.payment_id == payment_id)

        total = (
            await self.db.execute(select(func.count()).select_from(query.subquery()))
        ).scalar_one()
        query = (
            query.order_by(desc(Refund.created_at), desc(Refund.id))
            .offset((page - 1) * per_page)
            .limit(per_page)
        )
        result = await self.db.execute(query)
        return result.scalars().all(), total

    async def get_refund_admin(self, refund_id: UUID) -> Optional[Refund]:
        """Load refund, payment, order, and accounting details for the admin view."""
        return await self.db.scalar(
            select(Refund)
            .options(
                selectinload(Refund.payment).selectinload(Payment.order),
                selectinload(Refund.payment)
                .selectinload(Payment.refunds)
                .joinedload(Refund.accounting)
                .selectinload(RefundAccounting.allocations),
                joinedload(Refund.accounting).selectinload(RefundAccounting.allocations),
            )
            .where(Refund.id == refund_id)
            .execution_options(populate_existing=True)
        )

    async def get_payment_refunds(self, payment_id: UUID) -> Optional[Payment]:
        """Load a payment and its refund allocations for reconciliation history."""
        return await self.db.scalar(
            select(Payment)
            .options(
                selectinload(Payment.order),
                selectinload(Payment.refunds)
                .selectinload(Refund.accounting)
                .selectinload(RefundAccounting.allocations),
            )
            .where(Payment.id == payment_id)
            .execution_options(populate_existing=True)
        )

    async def list_admin(
        self,
        status: Optional[str] = None,
        method: Optional[str] = None,
        page: int = 1,
        per_page: int = 25,
    ) -> tuple[Sequence[Payment], int]:
        """Query payment records for admin reads using the caller's session."""
        q = select(Payment).options(selectinload(Payment.order))
        if status:
            q = q.where(Payment.status == PaymentStatus(status))
        if method:
            q = q.where(Payment.method == method)

        count_q = select(func.count()).select_from(q.subquery())
        total   = (await self.db.execute(count_q)).scalar_one()

        q = q.order_by(desc(Payment.created_at)).offset((page - 1) * per_page).limit(per_page)
        result = await self.db.execute(q)
        return result.scalars().all(), total
