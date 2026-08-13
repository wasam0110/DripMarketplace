"""Unit tests — Block 5: Orders. No DB required."""
import pytest
from pydantic import ValidationError

from app.schemas.order import (
    ShippingAddressInput,
    CreateOrderRequest,
    CreateGuestOrderRequest,
    CartItemInput,
    AddToCartRequest,
    UpdateCartItemRequest,
    ValidateCouponRequest,
    UpdateSellerOrderRequest,
    CancelOrderRequest,
)

VALID_ADDRESS = {
    "recipient_name": "Ali Khan",
    "phone":          "03001234567",
    "street":         "House 5, Street 12, DHA Phase 6",
    "city":           "Karachi",
    "province":       "Sindh",
}

VALID_ORDER = {
    "shipping_address": VALID_ADDRESS,
    "payment_method":   "cod",
}


class TestShippingAddress:
    def test_valid(self):
        addr = ShippingAddressInput(**VALID_ADDRESS)
        assert addr.city == "Karachi"

    def test_invalid_phone(self):
        with pytest.raises(ValidationError, match="Pakistani mobile"):
            ShippingAddressInput(**{**VALID_ADDRESS, "phone": "12345"})

    def test_phone_with_country_code(self):
        addr = ShippingAddressInput(**{**VALID_ADDRESS, "phone": "+923001234567"})
        assert addr.phone == "+923001234567"

    def test_short_street_rejected(self):
        with pytest.raises(ValidationError):
            ShippingAddressInput(**{**VALID_ADDRESS, "street": "abc"})


class TestCreateOrderRequest:
    def test_valid_cod(self):
        req = CreateOrderRequest(**VALID_ORDER)
        assert req.payment_method == "cod"

    def test_valid_jazzcash(self):
        req = CreateOrderRequest(**{**VALID_ORDER, "payment_method": "jazzcash"})
        assert req.payment_method == "jazzcash"

    def test_invalid_payment_method(self):
        with pytest.raises(ValidationError):
            CreateOrderRequest(**{**VALID_ORDER, "payment_method": "bitcoin"})


class TestCreateGuestOrderRequest:
    VALID_GUEST = {
        **VALID_ORDER,
        "guest_email": "guest@example.com",
        "guest_name":  "Ali Khan",
        "guest_phone": "03001234567",
        "items":       [{"variant_id": "00000000-0000-0000-0000-000000000001", "quantity": 1}],
    }

    def test_valid_guest_order(self):
        req = CreateGuestOrderRequest(**self.VALID_GUEST)
        assert req.guest_email == "guest@example.com"
        assert len(req.items) == 1

    def test_empty_items_rejected(self):
        with pytest.raises(ValidationError):
            CreateGuestOrderRequest(**{**self.VALID_GUEST, "items": []})

    def test_invalid_guest_phone(self):
        with pytest.raises(ValidationError):
            CreateGuestOrderRequest(**{**self.VALID_GUEST, "guest_phone": "12345"})

    def test_invalid_email(self):
        with pytest.raises(ValidationError):
            CreateGuestOrderRequest(**{**self.VALID_GUEST, "guest_email": "notanemail"})


class TestCartSchemas:
    def test_add_to_cart_valid(self):
        req = AddToCartRequest(
            variant_id="00000000-0000-0000-0000-000000000001", quantity=2
        )
        assert req.quantity == 2

    def test_add_to_cart_zero_rejected(self):
        with pytest.raises(ValidationError):
            AddToCartRequest(
                variant_id="00000000-0000-0000-0000-000000000001", quantity=0
            )

    def test_add_to_cart_over_limit(self):
        with pytest.raises(ValidationError):
            AddToCartRequest(
                variant_id="00000000-0000-0000-0000-000000000001", quantity=101
            )

    def test_update_cart_zero_allowed(self):
        req = UpdateCartItemRequest(quantity=0)
        assert req.quantity == 0


class TestCouponValidation:
    def test_valid(self):
        req = ValidateCouponRequest(code="DRIP10", subtotal=5000)
        assert req.code == "DRIP10"

    def test_zero_subtotal_rejected(self):
        with pytest.raises(ValidationError):
            ValidateCouponRequest(code="DRIP10", subtotal=0)


class TestUpdateSellerOrderRequest:
    def test_shipped_requires_tracking(self):
        with pytest.raises(ValidationError, match="tracking_number"):
            UpdateSellerOrderRequest(status="shipped")

    def test_shipped_with_tracking_ok(self):
        req = UpdateSellerOrderRequest(status="shipped", tracking_number="TCS-12345")
        assert req.tracking_number == "TCS-12345"

    def test_processing_no_tracking_ok(self):
        req = UpdateSellerOrderRequest(status="processing")
        assert req.tracking_number is None

    def test_invalid_status(self):
        with pytest.raises(ValidationError):
            UpdateSellerOrderRequest(status="cancelled")