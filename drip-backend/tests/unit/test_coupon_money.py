"""Discount rounding is explicit, exact and capped at the merchandise subtotal."""

from decimal import ROUND_DOWN, ROUND_UP, Decimal, localcontext

import pytest

from app.models.coupon import Coupon, DiscountType
from app.services.coupon_service import CouponService

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("context_rounding", [ROUND_DOWN, ROUND_UP])
@pytest.mark.parametrize(
    "kind,value,subtotal,expected",
    [
        ("percentage", "12.50", "100.05", "12.51"),
        ("percentage", "10.00", "100.05", "10.01"),
        ("percentage", "0.50", "1.00", "0.01"),
        ("percentage", "0.49", "1.00", "0.00"),
        ("percentage", "70.00", "9999999999.99", "6999999999.99"),
        ("fixed", "2.75", "100.05", "2.75"),
        ("fixed", "200.25", "100.05", "100.05"),
        ("fixed", "0.01", "100.05", "0.01"),
    ],
)
def test_discount_money_policy(context_rounding, kind, value, subtotal, expected):
    coupon = Coupon(discount_type=DiscountType(kind), discount_value=Decimal(value))
    with localcontext() as context:
        context.rounding = context_rounding
        result = CouponService._calc_discount(coupon, Decimal(subtotal))
    assert result == Decimal(expected)
    assert str(result) == expected
    assert Decimal("0") <= result <= Decimal(subtotal)
