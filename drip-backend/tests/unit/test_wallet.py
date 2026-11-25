"""Unit tests — Block 7: Wallet. No DB required."""
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.wallet import (
    AdminPayoutActionRequest,
    AdminWalletOverviewResponse,
    CommissionEntryResponse,
    CommissionSummary,
    PayoutResponse,
    WalletSummaryResponse,
    WalletTransactionResponse,
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

    @staticmethod
    def _transaction(amount: Decimal, balance_after: Decimal) -> WalletTransactionResponse:
        return WalletTransactionResponse(
            id=uuid4(),
            type="debit_adjustment",
            amount=amount,
            balance_after=balance_after,
            reference=None,
            note=None,
            created_at=datetime.now(UTC),
        )

    def test_transaction_amounts_serialize_with_two_decimal_places(self):
        response = self._transaction(Decimal("12.5"), Decimal("0"))

        assert response.model_dump(mode="json")["amount"] == "12.50"
        assert response.model_dump(mode="json")["balance_after"] == "0.00"

    @pytest.mark.parametrize(
        ("amount", "balance_after"),
        [
            (Decimal("12.345"), Decimal("0")),
            (Decimal("12.34"), Decimal("0.001")),
        ],
    )
    def test_transaction_amounts_reject_more_than_two_decimal_places(
        self, amount: Decimal, balance_after: Decimal
    ):
        with pytest.raises(ValidationError):
            self._transaction(amount, balance_after)

    def test_payout_amount_serializes_with_two_decimal_places(self):
        response = PayoutResponse(
            id=uuid4(),
            amount=Decimal("500"),
            payment_method="bank_transfer",
            payment_detail="account",
            status="requested",
            admin_note=None,
            requested_at=datetime.now(UTC),
            completed_at=None,
        )

        assert response.model_dump(mode="json")["amount"] == "500.00"

    def test_payout_amount_rejects_more_than_two_decimal_places(self):
        with pytest.raises(ValidationError):
            PayoutResponse(
                id=uuid4(),
                amount=Decimal("500.001"),
                payment_method="bank_transfer",
                payment_detail="account",
                status="requested",
                admin_note=None,
                requested_at=datetime.now(UTC),
                completed_at=None,
            )


class TestCommissionResponseMoney:
    COMMISSION_ENTRY_AMOUNT_FIELDS = (
        "gross_amount",
        "commission_amount",
        "seller_amount",
        "original_gross_amount",
        "original_commission_amount",
        "original_seller_amount",
        "refunded_gross_amount",
        "reversed_commission_amount",
        "reversed_seller_amount",
        "recovered_seller_amount",
        "settlement_offset_amount",
        "platform_shortfall_amount",
    )
    COMMISSION_SUMMARY_AMOUNT_FIELDS = (
        "total_gross",
        "total_commission",
        "total_net",
        "original_gross",
        "original_commission",
        "original_net",
        "total_refunded_gross",
        "total_reversed_commission",
        "total_reversed_seller",
        "total_recovered_seller",
        "total_settlement_offset",
        "total_platform_shortfall",
    )

    @staticmethod
    def _entry() -> CommissionEntryResponse:
        return CommissionEntryResponse(
            id=uuid4(),
            seller_order_id=uuid4(),
            gross_amount=Decimal("100.50"),
            commission_rate=0.15,
            commission_amount=Decimal("15.08"),
            seller_amount=Decimal("85.42"),
            original_gross_amount=Decimal("100.50"),
            original_commission_amount=Decimal("15.08"),
            original_seller_amount=Decimal("85.42"),
            refunded_gross_amount=Decimal("0"),
            reversed_commission_amount=Decimal("0"),
            reversed_seller_amount=Decimal("0"),
            recovered_seller_amount=Decimal("0"),
            settlement_offset_amount=Decimal("0"),
            platform_shortfall_amount=Decimal("0"),
            released_at=None,
            settled_at=datetime.now(UTC),
        )

    @staticmethod
    def _summary() -> CommissionSummary:
        return CommissionSummary(
            total_gross=Decimal("100.50"),
            total_commission=Decimal("15.08"),
            total_net=Decimal("85.42"),
            original_gross=Decimal("100.50"),
            original_commission=Decimal("15.08"),
            original_net=Decimal("85.42"),
            total_refunded_gross=Decimal("0"),
            total_reversed_commission=Decimal("0"),
            total_reversed_seller=Decimal("0"),
            total_recovered_seller=Decimal("0"),
            total_settlement_offset=Decimal("0"),
            total_platform_shortfall=Decimal("0"),
        )

    def test_commission_entry_amounts_serialize_with_two_decimal_places(self):
        body = self._entry().model_dump(mode="json")

        assert body["gross_amount"] == body["original_gross_amount"] == "100.50"
        assert body["commission_amount"] == body["original_commission_amount"] == "15.08"
        assert body["seller_amount"] == body["original_seller_amount"] == "85.42"
        assert all(
            body[name] == "0.00"
            for name in self.COMMISSION_ENTRY_AMOUNT_FIELDS[6:]
        )
        assert body["commission_rate"] == 0.15

    def test_commission_entry_rejects_more_than_two_decimal_places(self):
        body = self._entry().model_dump()
        body["platform_shortfall_amount"] = Decimal("0.001")

        with pytest.raises(ValidationError):
            CommissionEntryResponse(**body)

    def test_commission_summary_amounts_serialize_with_two_decimal_places(self):
        body = self._summary().model_dump(mode="json")

        assert body["total_gross"] == body["original_gross"] == "100.50"
        assert body["total_commission"] == body["original_commission"] == "15.08"
        assert body["total_net"] == body["original_net"] == "85.42"
        assert all(
            body[name] == "0.00"
            for name in self.COMMISSION_SUMMARY_AMOUNT_FIELDS[6:]
        )

    def test_commission_summary_rejects_more_than_two_decimal_places(self):
        body = self._summary().model_dump()
        body["total_net"] = Decimal("0.001")

        with pytest.raises(ValidationError):
            CommissionSummary(**body)


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
