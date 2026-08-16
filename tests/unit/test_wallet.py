"""Unit tests — Block 7: Wallet. No DB required."""
import pytest
from decimal import Decimal
from pydantic import ValidationError

from app.services.commission_service import COMMISSION_RATE
from app.schemas.wallet import WithdrawalRequest, AdminPayoutActionRequest


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