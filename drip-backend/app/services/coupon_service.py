"""services / coupon service.

Business operations connecting API handlers, persistence, and provider integrations.
"""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessRuleError
from app.models.coupon import Coupon, CouponUsage, DiscountType
from app.schemas.order import ValidateCouponRequest, CouponValidationResponse


class CouponService:
    def __init__(self, db: AsyncSession) -> None:
        """Bind CouponService to its injected dependencies for subsequent operations."""
        self.db = db

    async def validate(
        self,
        payload: ValidateCouponRequest,
        user_id: Optional[UUID] = None,
    ) -> CouponValidationResponse:
        """Check coupon eligibility and calculate the preview discount for checkout."""
        coupon = await self._get_valid_coupon(payload.code, payload.subtotal, user_id)
        discount_amount = self._calc_discount(coupon, payload.subtotal)
        return CouponValidationResponse(
            code            = coupon.code,
            discount_type   = coupon.discount_type.value,
            discount_value  = coupon.discount_value,
            discount_amount = discount_amount,
            new_subtotal    = (payload.subtotal - discount_amount).quantize(Decimal("0.01")),
        )

    async def apply_to_order(
        self,
        code: str,
        subtotal: Decimal,
        user_id: UUID,
        order_id: UUID,
    ) -> Decimal:
        """Validate, calculate discount, record usage, increment uses_count."""
        coupon = await self._get_valid_coupon(code, subtotal, user_id)
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
        self, code: str, subtotal: Decimal, user_id: Optional[UUID], *, lock: bool = False
    ) -> Coupon:
        """Check activation dates, usage limits, and checkout constraints for a coupon."""
        query = select(Coupon).where(Coupon.code == code.upper())
        if lock:
            query = query.with_for_update()
        result = await self.db.execute(query)
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
        if subtotal < coupon.min_order_amount:
            raise BusinessRuleError(
                f"Minimum order amount for this coupon is PKR {coupon.min_order_amount:,.2f}"
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
        """Calculate the coupon's capped, currency-rounded discount."""
        # Round the discount once, in PKR major units, before seller allocation.
        # Explicit half-up matches the ledger money policy and avoids dependence
        # on the caller's Decimal rounding context.
        if coupon.discount_type == DiscountType.percentage:
            discount = subtotal * coupon.discount_value / 100
        else:
            discount = coupon.discount_value
        return min(discount, subtotal).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
