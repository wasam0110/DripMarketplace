from __future__ import annotations

from decimal import Decimal
from uuid import UUID
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessRuleError, NotFoundError
from app.models.coupon import Coupon, CouponUsage, DiscountType
from app.schemas.order import ValidateCouponRequest, CouponValidationResponse


class CouponService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def validate(
        self,
        payload: ValidateCouponRequest,
        user_id: Optional[UUID] = None,
    ) -> CouponValidationResponse:
        coupon = await self._get_valid_coupon(payload.code, payload.subtotal, user_id)
        discount_amount = self._calc_discount(coupon, Decimal(payload.subtotal))
        return CouponValidationResponse(
            code            = coupon.code,
            discount_type   = coupon.discount_type.value,
            discount_value  = int(coupon.discount_value),
            discount_amount = int(discount_amount),
            new_subtotal    = max(0, payload.subtotal - int(discount_amount)),
        )

    async def apply_to_order(
        self,
        code: str,
        subtotal: Decimal,
        user_id: UUID,
        order_id: UUID,
    ) -> Decimal:
        """Validate, calculate discount, record usage, increment uses_count."""
        coupon = await self._get_valid_coupon(code, int(subtotal), user_id)
        discount = self._calc_discount(coupon, subtotal)

        # Record usage
        usage = CouponUsage(
            coupon_id=coupon.id, user_id=user_id, order_id=order_id
        )
        self.db.add(usage)

        # Increment uses_count
        await self.db.execute(
            update(Coupon)
            .where(Coupon.id == coupon.id)
            .values(uses_count=Coupon.uses_count + 1)
        )
        return discount

    # ── Helpers ────────────────────────────────────────────────────────────────

    async def _get_valid_coupon(
        self, code: str, subtotal: int, user_id: Optional[UUID]
    ) -> Coupon:
        result = await self.db.execute(
            select(Coupon).where(Coupon.code == code.upper())
        )
        coupon = result.scalar_one_or_none()

        if not coupon:
            raise BusinessRuleError("Coupon code not found")
        if not coupon.is_active:
            raise BusinessRuleError("This coupon is no longer active")

        now = datetime.now(timezone.utc)
        if coupon.valid_from and now < coupon.valid_from.replace(tzinfo=timezone.utc):
            raise BusinessRuleError("This coupon is not yet valid")
        if coupon.valid_until and now > coupon.valid_until.replace(tzinfo=timezone.utc):
            raise BusinessRuleError("This coupon has expired")
        if coupon.max_uses and coupon.uses_count >= coupon.max_uses:
            raise BusinessRuleError("This coupon has reached its usage limit")
        if subtotal < int(coupon.min_order_amount):
            raise BusinessRuleError(
                f"Minimum order amount for this coupon is PKR {int(coupon.min_order_amount):,}"
            )

        if user_id:
            # Check per-customer usage
            usage_count_result = await self.db.execute(
                select(CouponUsage).where(
                    CouponUsage.coupon_id == coupon.id,
                    CouponUsage.user_id == user_id,
                )
            )
            user_usages = len(usage_count_result.scalars().all())
            if user_usages >= coupon.max_uses_per_customer:
                raise BusinessRuleError("You have already used this coupon")

        return coupon

    @staticmethod
    def _calc_discount(coupon: Coupon, subtotal: Decimal) -> Decimal:
        if coupon.discount_type == DiscountType.percentage:
            return (subtotal * coupon.discount_value / 100).quantize(Decimal("0.01"))
        return min(coupon.discount_value, subtotal)