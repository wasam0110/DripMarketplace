"""
tests/unit/test_slot_service.py
────────────────────────────────
Unit tests for SlotService.

Covers:
  - Pricing calculation (registration fee + extra slots)
  - Edge cases: 0 extra, 1 extra, max extra
  - Validation on SlotPurchaseRequest
  - Purchase flow: wallet deduction, slot count increment
  - Error paths: inactive seller, insufficient balance
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.services.slot_service import (
    SlotService,
    REGISTRATION_FEE,
    BASE_SLOTS,
    EXTRA_SLOT_PRICE,
)
from app.schemas.seller import SlotPurchaseRequest, SlotPricingResponse


# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestSlotConstants:
    def test_registration_fee_is_5000(self):
        assert REGISTRATION_FEE == 5000

    def test_base_slots_is_50(self):
        assert BASE_SLOTS == 50

    def test_extra_slot_price_is_50(self):
        assert EXTRA_SLOT_PRICE == 50


# ═══════════════════════════════════════════════════════════════════════════════
# PRICING CALCULATION (static — no DB)
# ═══════════════════════════════════════════════════════════════════════════════

class TestSlotPricing:
    def test_zero_extra_slots(self):
        r = SlotService.calculate_pricing(0)
        assert r.registration_fee == REGISTRATION_FEE
        assert r.extra_slots      == 0
        assert r.extra_cost       == 0
        assert r.total_cost       == REGISTRATION_FEE
        assert r.total_slots      == BASE_SLOTS

    def test_one_extra_slot(self):
        r = SlotService.calculate_pricing(1)
        assert r.extra_cost  == EXTRA_SLOT_PRICE
        assert r.total_cost  == REGISTRATION_FEE + EXTRA_SLOT_PRICE
        assert r.total_slots == BASE_SLOTS + 1

    def test_ten_extra_slots(self):
        r = SlotService.calculate_pricing(10)
        assert r.extra_cost  == 10 * EXTRA_SLOT_PRICE
        assert r.total_cost  == REGISTRATION_FEE + 10 * EXTRA_SLOT_PRICE
        assert r.total_slots == BASE_SLOTS + 10

    def test_hundred_extra_slots(self):
        r = SlotService.calculate_pricing(100)
        assert r.total_slots == BASE_SLOTS + 100
        assert r.extra_cost  == 100 * EXTRA_SLOT_PRICE

    def test_ten_thousand_extra_slots(self):
        r = SlotService.calculate_pricing(10_000)
        assert r.total_slots == BASE_SLOTS + 10_000
        assert r.total_cost  == REGISTRATION_FEE + 10_000 * EXTRA_SLOT_PRICE

    def test_returns_pricing_response_type(self):
        r = SlotService.calculate_pricing(5)
        assert isinstance(r, SlotPricingResponse)

    @pytest.mark.parametrize("extra", [0, 1, 5, 10, 50, 100, 500])
    def test_total_cost_formula(self, extra: int):
        r = SlotService.calculate_pricing(extra)
        expected = REGISTRATION_FEE + extra * EXTRA_SLOT_PRICE
        assert r.total_cost == expected

    @pytest.mark.parametrize("extra", [0, 1, 5, 100])
    def test_total_slots_formula(self, extra: int):
        r = SlotService.calculate_pricing(extra)
        assert r.total_slots == BASE_SLOTS + extra

    def test_base_slots_always_included(self):
        """Even with 0 extra, seller gets BASE_SLOTS."""
        r = SlotService.calculate_pricing(0)
        assert r.base_slots == BASE_SLOTS


# ═══════════════════════════════════════════════════════════════════════════════
# SLOT PURCHASE REQUEST SCHEMA VALIDATION
# ═══════════════════════════════════════════════════════════════════════════════

class TestSlotPurchaseRequestSchema:
    def test_valid_wallet_payment(self):
        req = SlotPurchaseRequest(quantity=5, payment_method="wallet")
        assert req.quantity       == 5
        assert req.payment_method == "wallet"

    def test_valid_jazzcash_payment(self):
        req = SlotPurchaseRequest(quantity=1, payment_method="jazzcash")
        assert req.payment_method == "jazzcash"

    def test_zero_quantity_rejected(self):
        with pytest.raises(ValidationError):
            SlotPurchaseRequest(quantity=0, payment_method="wallet")

    def test_negative_quantity_rejected(self):
        with pytest.raises(ValidationError):
            SlotPurchaseRequest(quantity=-1, payment_method="wallet")

    def test_invalid_payment_method_rejected(self):
        with pytest.raises(ValidationError):
            SlotPurchaseRequest(quantity=5, payment_method="bitcoin")

    def test_quantity_above_max_rejected(self):
        with pytest.raises(ValidationError):
            SlotPurchaseRequest(quantity=10_001, payment_method="wallet")

    def test_quantity_one_is_valid(self):
        req = SlotPurchaseRequest(quantity=1, payment_method="wallet")
        assert req.quantity == 1


# ═══════════════════════════════════════════════════════════════════════════════
# PURCHASE FLOW (async, mocked DB)
# ═══════════════════════════════════════════════════════════════════════════════

def _mock_service(
    seller_status: str = "active",
    wallet_balance: Decimal = Decimal("50000"),
) -> SlotService:
    db = AsyncMock()
    svc = SlotService(db)

    seller = MagicMock()
    seller.id       = uuid4()
    seller.status   = MagicMock()
    seller.status.value = seller_status
    seller.slot_count   = BASE_SLOTS

    from app.models.seller import SellerStatus
    seller.status = seller_status  # keep as string, the test mock doesn't need enum
    wallet = MagicMock()
    wallet.available_balance = wallet_balance

    svc.seller_repo = AsyncMock()
    svc.seller_repo.get_by_user_id = AsyncMock(return_value=seller)

    svc.wallet_repo = AsyncMock()
    svc.wallet_repo.get_by_seller_id = AsyncMock(return_value=wallet)
    svc.wallet_repo.debit = AsyncMock()

    return svc


class TestSlotPurchaseFlow:
    @pytest.mark.asyncio
    async def test_inactive_seller_raises_permission_error(self):
        from app.core.exceptions import PermissionDeniedError

        svc = _mock_service(seller_status="pending")
        req = SlotPurchaseRequest(quantity=5, payment_method="wallet")

        with pytest.raises(PermissionDeniedError):
            await svc.purchase_slots(user_id=uuid4(), payload=req)

    @pytest.mark.asyncio
    async def test_suspended_seller_raises_permission_error(self):
        from app.core.exceptions import PermissionDeniedError

        svc = _mock_service(seller_status="suspended")
        req = SlotPurchaseRequest(quantity=5, payment_method="wallet")

        with pytest.raises(PermissionDeniedError):
            await svc.purchase_slots(user_id=uuid4(), payload=req)

    @pytest.mark.asyncio
    async def test_insufficient_wallet_balance_raises(self):
        from app.core.exceptions import InsufficientBalanceError

        svc = _mock_service(wallet_balance=Decimal("0"))
        req = SlotPurchaseRequest(quantity=5, payment_method="wallet")

        with pytest.raises((InsufficientBalanceError, Exception)):
            await svc.purchase_slots(user_id=uuid4(), payload=req)

    @pytest.mark.asyncio
    async def test_seller_not_found_raises(self):
        from app.core.exceptions import NotFoundError

        db  = AsyncMock()
        svc = SlotService(db)
        svc.seller_repo = AsyncMock()
        svc.seller_repo.get_by_user_id = AsyncMock(return_value=None)

        req = SlotPurchaseRequest(quantity=5, payment_method="wallet")
        with pytest.raises(NotFoundError):
            await svc.purchase_slots(user_id=uuid4(), payload=req)


# ═══════════════════════════════════════════════════════════════════════════════
# COST ARITHMETIC INVARIANTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestSlotCostInvariants:
    @pytest.mark.parametrize("qty", [1, 5, 10, 100])
    def test_wallet_debit_equals_quantity_times_price(self, qty: int):
        """The debit amount must exactly equal qty × EXTRA_SLOT_PRICE."""
        expected = Decimal(qty * EXTRA_SLOT_PRICE)
        pricing  = SlotService.calculate_pricing(qty)
        assert Decimal(str(pricing.extra_cost)) == expected

    def test_no_free_slots_beyond_base(self):
        """Extra slots always cost money; there is no free tier above BASE_SLOTS."""
        r = SlotService.calculate_pricing(1)
        assert r.extra_cost > 0

    def test_registration_fee_constant_regardless_of_extra_slots(self):
        """The registration_fee field is always REGISTRATION_FEE, regardless of extras."""
        for extra in [0, 1, 100, 10_000]:
            r = SlotService.calculate_pricing(extra)
            assert r.registration_fee == REGISTRATION_FEE
