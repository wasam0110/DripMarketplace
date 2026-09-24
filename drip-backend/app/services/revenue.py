"""Recorded seller fees; legacy approval dates are not payment receipts."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.seller import Seller
from app.models.wallet import WalletTransaction, WalletTxType


async def seller_fee_revenue(db: AsyncSession, since: datetime) -> Decimal:
    registration = await db.scalar(select(func.coalesce(func.sum(Seller.registration_fee), 0)).where(
        Seller.registration_paid_at >= since,
    ))
    slots = await db.scalar(select(func.coalesce(func.sum(WalletTransaction.amount), 0)).where(
        WalletTransaction.created_at >= since,
        WalletTransaction.type == WalletTxType.debit_adjustment,
        WalletTransaction.reference.like("slot-purchase:%"),
    ))
    return Decimal(registration or 0) + Decimal(slots or 0)
