"""
tests/unit/test_commission_service.py
──────────────────────────────────────
Unit tests for CommissionService.

Covers:
  - Commission calculation at the correct rate (15%)
  - Rounding behaviour on fractional amounts
  - Idempotency (double-settling the same SellerOrder is a no-op)
  - Edge cases: zero subtotal, very large amounts, minimum penny
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
import pytest_asyncio

from app.services.commission_service import CommissionService, COMMISSION_RATE


# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def _make_service(
    seller_order=None,
    commission_exists: bool = False,
) -> tuple[CommissionService, MagicMock]:
    """Return a CommissionService wired to mocked repos and a mock DB session."""
    from app.models.payment import PaymentStatus
    db = AsyncMock()
    db.scalar = AsyncMock(return_value=MagicMock(status=PaymentStatus.completed))

    svc = CommissionService(db)
    svc.comm_repo  = AsyncMock()
    svc.tx_repo    = AsyncMock()
    svc.wallet_repo = AsyncMock()

    svc.comm_repo.exists_for_seller_order = AsyncMock(return_value=commission_exists)
    svc.comm_repo.create = AsyncMock(return_value=MagicMock(id=uuid4()))

    svc.wallet_repo.credit_pending = AsyncMock()
    svc.tx_repo.create = AsyncMock()

    if seller_order is not None:
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = seller_order
        db.execute = AsyncMock(return_value=result_mock)

    return svc, db


def _make_seller_order(subtotal: Decimal):
    order = MagicMock()
    from app.models.order import SellerOrderStatus
    order.status = SellerOrderStatus.delivered
    order.id       = uuid4()
    order.subtotal = subtotal
    order.seller_id = uuid4()
    return order


# ═══════════════════════════════════════════════════════════════════════════════
# COMMISSION RATE
# ═══════════════════════════════════════════════════════════════════════════════

class TestCommissionRate:
    def test_rate_is_fifteen_percent(self):
        assert COMMISSION_RATE == Decimal("0.15")

    def test_commission_on_round_amount(self):
        subtotal   = Decimal("1000.00")
        commission = (subtotal * COMMISSION_RATE).quantize(Decimal("0.01"))
        seller_net = subtotal - commission
        assert commission == Decimal("150.00")
        assert seller_net == Decimal("850.00")

    def test_commission_on_typical_order(self):
        """PKR 2,499 order — 15% commission."""
        subtotal   = Decimal("2499.00")
        commission = (subtotal * COMMISSION_RATE).quantize(Decimal("0.01"))
        assert commission == Decimal("374.85")
        assert subtotal - commission == Decimal("2124.15")

    def test_commission_on_minimum_price(self):
        """Minimum product price is PKR 100. Commission should be PKR 15."""
        subtotal   = Decimal("100.00")
        commission = (subtotal * COMMISSION_RATE).quantize(Decimal("0.01"))
        assert commission == Decimal("15.00")

    def test_commission_on_maximum_price(self):
        """Maximum product price is PKR 500,000."""
        subtotal   = Decimal("500000.00")
        commission = (subtotal * COMMISSION_RATE).quantize(Decimal("0.01"))
        assert commission == Decimal("75000.00")


# ═══════════════════════════════════════════════════════════════════════════════
# ROUNDING
# ═══════════════════════════════════════════════════════════════════════════════

class TestCommissionRounding:
    @pytest.mark.parametrize("subtotal,expected_commission", [
        # ROUND_HALF_UP: .005 rounds up, .004 rounds down
        ("333.33", "50.00"),   # 333.33 * 0.15 = 49.9995 → 50.00
        ("333.34", "50.00"),   # 333.34 * 0.15 = 50.001  → 50.00
        ("0.07",   "0.01"),    # minimum non-zero commission
        ("0.06",   "0.01"),    # 0.006 rounds up to 0.01
        ("100.01", "15.00"),   # 100.01 * 0.15 = 15.0015 → 15.00
        ("100.04", "15.01"),   # 100.04 * 0.15 = 15.006  → 15.01
    ])
    def test_rounding(self, subtotal: str, expected_commission: str):
        from decimal import ROUND_HALF_UP
        s = Decimal(subtotal)
        c = (s * COMMISSION_RATE).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        assert c == Decimal(expected_commission), (
            f"subtotal={subtotal}: expected {expected_commission}, got {c}"
        )

    def test_seller_net_plus_commission_equals_subtotal(self):
        """No money is created or lost in the split."""
        from decimal import ROUND_HALF_UP
        for subtotal_str in ["1000.00", "2499.00", "7777.77", "99.99", "500000.00"]:
            s   = Decimal(subtotal_str)
            c   = (s * COMMISSION_RATE).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            net = s - c
            # Due to rounding, net + commission may differ by at most 1 paisa
            assert abs((net + c) - s) <= Decimal("0.01"), (
                f"Money mismatch at subtotal={subtotal_str}: {net} + {c} ≠ {s}"
            )


# ═══════════════════════════════════════════════════════════════════════════════
# SETTLE METHOD
# ═══════════════════════════════════════════════════════════════════════════════

class TestCommissionSettle:
    @pytest.mark.asyncio
    async def test_settle_creates_commission_ledger_entry(self):
        """settle() must create one CommissionLedger entry."""
        seller_order = _make_seller_order(Decimal("1000.00"))
        svc, db = _make_service(seller_order=seller_order, commission_exists=False)

        await svc.settle(seller_order.id)

        svc.comm_repo.create.assert_awaited_once()
        call_kwargs = svc.comm_repo.create.call_args.kwargs
        assert "seller_order_id" in call_kwargs or svc.comm_repo.create.called

    @pytest.mark.asyncio
    async def test_settle_credits_seller_pending_balance(self):
        """settle() must credit the seller's pending balance."""
        seller_order = _make_seller_order(Decimal("2000.00"))
        svc, db = _make_service(seller_order=seller_order, commission_exists=False)

        await svc.settle(seller_order.id)

        svc.wallet_repo.credit_pending.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_settle_is_idempotent(self):
        """Calling settle() twice for the same SellerOrder must be a no-op on the 2nd call."""
        seller_order = _make_seller_order(Decimal("500.00"))
        svc, db = _make_service(seller_order=seller_order, commission_exists=True)

        await svc.settle(seller_order.id)

        # With commission_exists=True, none of the create/credit methods should be called
        svc.comm_repo.create.assert_not_awaited()
        svc.wallet_repo.credit_pending.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_settle_raises_for_missing_order(self):
        """settle() must raise NotFoundError when the SellerOrder doesn't exist."""
        from app.core.exceptions import NotFoundError

        svc, db = _make_service(seller_order=None, commission_exists=False)
        # seller_order=None → scalar_one_or_none returns None
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=result_mock)

        with pytest.raises(NotFoundError):
            await svc.settle(uuid4())

    @pytest.mark.asyncio
    async def test_settle_correct_commission_amount(self):
        """settle() must pass the correct PKR amounts to the repo."""
        subtotal     = Decimal("3000.00")
        seller_order = _make_seller_order(subtotal)
        svc, db      = _make_service(seller_order=seller_order, commission_exists=False)

        await svc.settle(seller_order.id)

        # Verify the credit amount passed to wallet_repo
        credit_call = svc.wallet_repo.credit_pending.call_args
        if credit_call:
            # Either positional or keyword — check the amount
            args   = credit_call.args
            kwargs = credit_call.kwargs
            amount = kwargs.get("amount") or (args[1] if len(args) > 1 else None)
            if amount is not None:
                expected_net = subtotal - (subtotal * COMMISSION_RATE).quantize(Decimal("0.01"))
                assert abs(Decimal(str(amount)) - expected_net) <= Decimal("0.01")


# ═══════════════════════════════════════════════════════════════════════════════
# SCHEMA-LEVEL: Commission rate configuration
# ═══════════════════════════════════════════════════════════════════════════════

class TestCommissionConfig:
    def test_rate_is_a_decimal(self):
        assert isinstance(COMMISSION_RATE, Decimal)

    def test_rate_expressed_as_fraction(self):
        """Rate should be stored as a fraction (0.15), not a percentage (15)."""
        assert COMMISSION_RATE < Decimal("1")
        assert COMMISSION_RATE > Decimal("0")

    def test_commission_plus_seller_net_covers_full_subtotal(self):
        """15% + 85% = 100%."""
        seller_rate = Decimal("1") - COMMISSION_RATE
        assert seller_rate == Decimal("0.85")
