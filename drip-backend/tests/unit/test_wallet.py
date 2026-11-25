"""Unit tests — Block 7: Wallet. No DB required."""
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas.wallet import (
    AdminPayoutActionRequest,
    AdminWalletOverviewResponse,
    WalletSummaryResponse,
    WithdrawalRequest,
)
from app.services.commission_service import COMMISSION_RATE


class TestWalletResponseMoney:
    def test_summary_amounts_serialize_with_two_decimal_places(self):
        response = WalletSummaryResponse(
            available_balance=Decimal("12.5"),
            pending_balance=Decimal("0"),
            total_earned=Decimal("20.00"),
            total_commission=Decimal("3.45"),
            minimum_withdrawal_amount=Decimal("500"),
            maximum_withdrawal_amount=Decimal("200000"),
        )

        assert response.model_dump(mode="json") == {
            "available_balance": "12.50",
            "pending_balance": "0.00",
            "total_earned": "20.00",
            "total_commission": "3.45",
            "minimum_withdrawal_amount": "500.00",
            "maximum_withdrawal_amount": "200000.00",
        }

    def test_summary_amounts_reject_more_than_two_decimal_places(self):
        with pytest.raises(ValidationError):
            WalletSummaryResponse(
                available_balance=Decimal("12.345"),
                pending_balance=Decimal("0"),
                total_earned=Decimal("20.00"),
                total_commission=Decimal("3.45"),
                minimum_withdrawal_amount=Decimal("500"),
                maximum_withdrawal_amount=Decimal("200000"),
            )

    def test_admin_overview_amounts_serialize_with_two_decimal_places(self):
        response = AdminWalletOverviewResponse(
            total_available_balance=Decimal("12.5"),
            total_pending_balance=Decimal("0"),
            total_payouts_pending=1,
            total_payouts_completed=2,
        )

        assert response.model_dump(mode="json") == {
            "total_available_balance": "12.50",
            "total_pending_balance": "0.00",
            "total_payouts_pending": 1,
            "total_payouts_completed": 2,
        }


class TestCommissionMath:
    def test_rate_is_fifteen_percent(self):
        assert COMMISSION_RATE == Decimal("0.15")

    def test_seller_gets_85_percent(self):
        gross      = Decimal("1000.00")
        commission = (gross * COMMISSION_RATE).quantize(Decimal("0.01"))
        seller     = gross - commission
        assert commission == Decimal("150.00")
        assert seller     == Decimal("850.00")

    def test_commission_plus_seller_equals_gross(self):
        for gross in [500, 1000, 3750, 9999]:
            g = Decimal(gross)
            c = (g * COMMISSION_RATE).quantize(Decimal("0.01"))
            s = g - c
            assert c + s == g


class TestWithdrawalSchema:
    VALID = {"amount": 500, "bank_account_id": "00000000-0000-0000-0000-000000000001"}

    def test_valid_minimum(self):
        req = WithdrawalRequest(**self.VALID)
        assert req.amount == 500

    def test_valid_large(self):
        req = WithdrawalRequest(amount=200_000, bank_account_id=self.VALID["bank_account_id"])
        assert req.amount == 200_000

    def test_below_minimum_rejected(self):
        with pytest.raises(ValidationError):
            WithdrawalRequest(amount=499, bank_account_id=self.VALID["bank_account_id"])

    def test_above_maximum_rejected(self):
        with pytest.raises(ValidationError):
            WithdrawalRequest(amount=200_001, bank_account_id=self.VALID["bank_account_id"])

    def test_zero_rejected(self):
        with pytest.raises(ValidationError):
            WithdrawalRequest(amount=0, bank_account_id=self.VALID["bank_account_id"])


class TestAdminPayoutSchema:
    def test_valid_with_note(self):
        req = AdminPayoutActionRequest(admin_note="Approved after verification")
        assert req.admin_note == "Approved after verification"

    def test_valid_no_note(self):
        req = AdminPayoutActionRequest()
        assert req.admin_note is None
