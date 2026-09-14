"""
Unit tests — Block 3: Sellers & Slots
Run: pytest tests/unit/test_sellers.py -v
No DB required.
"""
import pytest
from pydantic import ValidationError

from app.services.slot_service import SlotService, REGISTRATION_FEE, BASE_SLOTS, EXTRA_SLOT_PRICE
from app.services.seller_service import _slugify
from app.schemas.seller import (
    SellerRegistrationRequest,
    SlotPurchaseRequest,
    SellerProfileUpdateRequest,
    CreateBankAccountRequest,
    UpdateOrderStatusRequest,
)

VALID_REG = {
    "email":           "seller@drip.pk",
    "password":        "Password123",
    "first_name":      "Ali",
    "brand_name":      "Street Drip",
    "description":     "Premium Pakistani streetwear for the culture",
    "return_policy":   "No returns on discounted items",
    "whatsapp_number": "03001234567",
    "extra_slots":     0,
}


class TestSlotPricing:
    def test_zero_extra(self):
        r = SlotService.calculate_pricing(0)
        assert r.total_cost  == REGISTRATION_FEE
        assert r.total_slots == BASE_SLOTS
        assert r.extra_cost  == 0

    def test_ten_extra(self):
        r = SlotService.calculate_pricing(10)
        assert r.extra_cost  == 500
        assert r.total_cost  == 5500
        assert r.total_slots == 60

    def test_hundred_extra(self):
        r = SlotService.calculate_pricing(100)
        assert r.total_cost  == 10_000
        assert r.total_slots == 150

    def test_price_per_slot_is_fifty(self):
        assert EXTRA_SLOT_PRICE == 50


class TestSlugify:
    def test_basic(self):
        assert _slugify("DRIP Brands PK") == "drip-brands-pk"

    def test_strips_non_ascii(self):
        assert _slugify("Brand & Co") == "brand-co"

    def test_underscores_become_dashes(self):
        assert _slugify("my_brand") == "my-brand"

    def test_max_length(self):
        assert len(_slugify("A" * 300)) <= 120


class TestSellerRegistrationSchema:
    def test_valid(self):
        req = SellerRegistrationRequest(**VALID_REG)
        assert req.brand_name == "Street Drip"

    def test_invalid_phone(self):
        with pytest.raises(ValidationError, match="Pakistani mobile"):
            SellerRegistrationRequest(**{**VALID_REG, "whatsapp_number": "0300123"})

    def test_phone_with_country_code(self):
        req = SellerRegistrationRequest(**{**VALID_REG, "whatsapp_number": "+923001234567"})
        assert req.whatsapp_number == "+923001234567"

    def test_password_no_uppercase(self):
        with pytest.raises(ValidationError, match="uppercase"):
            SellerRegistrationRequest(**{**VALID_REG, "password": "password123"})

    def test_password_no_digit(self):
        with pytest.raises(ValidationError, match="digit"):
            SellerRegistrationRequest(**{**VALID_REG, "password": "PasswordABC"})

    def test_negative_extra_slots(self):
        with pytest.raises(ValidationError):
            SellerRegistrationRequest(**{**VALID_REG, "extra_slots": -1})

    def test_description_too_short(self):
        with pytest.raises(ValidationError):
            SellerRegistrationRequest(**{**VALID_REG, "description": "Short"})


class TestSlotPurchaseSchema:
    def test_valid(self):
        req = SlotPurchaseRequest(quantity=10, payment_method="wallet")
        assert req.quantity == 10

    def test_zero_quantity_rejected(self):
        with pytest.raises(ValidationError):
            SlotPurchaseRequest(quantity=0, payment_method="wallet")

    def test_invalid_payment_method(self):
        with pytest.raises(ValidationError):
            SlotPurchaseRequest(quantity=5, payment_method="stripe")


class TestProfileUpdateSchema:
    def test_empty_rejected(self):
        with pytest.raises(ValidationError, match="At least one"):
            SellerProfileUpdateRequest()

    def test_single_field_ok(self):
        req = SellerProfileUpdateRequest(description="New description text here")
        assert req.description == "New description text here"

    def test_bad_hex_color(self):
        with pytest.raises(ValidationError):
            SellerProfileUpdateRequest(brand_color="red")

    def test_valid_hex_color(self):
        req = SellerProfileUpdateRequest(brand_color="#DFFF00")
        assert req.brand_color == "#DFFF00"


class TestBankAccountSchema:
    def test_empty_rejected(self):
        with pytest.raises(ValidationError, match="Provide either"):
            CreateBankAccountRequest()

    def test_jazzcash_only_ok(self):
        req = CreateBankAccountRequest(jazzcash_number="03001234567")
        assert req.jazzcash_number == "03001234567"

    def test_bank_fields_ok(self):
        req = CreateBankAccountRequest(
            bank_name="Meezan Bank",
            account_number="01234567890123",
        )
        assert req.bank_name == "Meezan Bank"


class TestOrderStatusSchema:
    def test_shipped_without_tracking_rejected(self):
        with pytest.raises(ValidationError, match="tracking_number"):
            UpdateOrderStatusRequest(status="shipped")

    def test_shipped_with_tracking_ok(self):
        req = UpdateOrderStatusRequest(status="shipped", tracking_number="TCS-12345")
        assert req.tracking_number == "TCS-12345"

    def test_processing_no_tracking_ok(self):
        req = UpdateOrderStatusRequest(status="processing")
        assert req.tracking_number is None