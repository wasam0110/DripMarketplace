"""Unit tests — Block 6: Payments. No DB required."""
import pytest
from pydantic import ValidationError

from app.integrations.jazzcash import JazzCashClient
from app.integrations.easypaisa import EasypaisaClient
from app.schemas.payment import (
    InitiatePaymentRequest,
    RetryPaymentRequest,
    RefundRequest,
)


class TestJazzCashHMAC:
    def setup_method(self):
        self.jc = JazzCashClient(
            merchant_id    = "TEST_MERCHANT",
            password       = "TEST_PASS",
            integrity_salt = "test_salt_123",
        )

    def test_hash_deterministic(self):
        params = {"pp_Amount": "50000", "pp_MerchantID": "TEST", "pp_TxnRefNo": "T001"}
        h1 = self.jc.build_secure_hash(params)
        h2 = self.jc.build_secure_hash(params)
        assert h1 == h2

    def test_hash_excludes_secure_hash_key(self):
        params = {"pp_Amount": "50000", "pp_SecureHash": "should_be_excluded"}
        h = self.jc.build_secure_hash(params)
        assert isinstance(h, str)
        assert len(h) == 64  # SHA-256 hex = 64 chars

    def test_verify_callback_success(self):
        params = {"pp_Amount": "50000", "pp_TxnRefNo": "T001"}
        correct_hash = self.jc.build_secure_hash(params)
        callback     = {**params, "pp_SecureHash": correct_hash}
        assert self.jc.verify_callback(callback) is True

    def test_verify_callback_tampered(self):
        params = {"pp_Amount": "50000", "pp_TxnRefNo": "T001"}
        callback = {**params, "pp_SecureHash": "BADHASH"}
        assert self.jc.verify_callback(callback) is False

    def test_success_code_000(self):
        assert self.jc.is_success("000") is True

    def test_failure_code_other(self):
        assert self.jc.is_success("111") is False
        assert self.jc.is_success("")    is False


class TestEasypaisaHash:
    def setup_method(self):
        self.ep = EasypaisaClient(
            store_id   = "TEST_STORE",
            store_key  = "test_key_abc",
            account_no = "03001234567",
        )

    def test_hash_deterministic(self):
        params = {"amount": "5000", "orderId": "EP001"}
        h1 = self.ep.build_hash(params, "test_key_abc")
        h2 = self.ep.build_hash(params, "test_key_abc")
        assert h1 == h2

    def test_hash_different_key(self):
        params = {"amount": "5000"}
        h1 = self.ep.build_hash(params, "key1")
        h2 = self.ep.build_hash(params, "key2")
        assert h1 != h2

    def test_success_code(self):
        assert self.ep.is_success("0000") is True
        assert self.ep.is_success("0001") is False


class TestPaymentSchemas:
    def test_initiate_valid(self):
        req = InitiatePaymentRequest(order_id="00000000-0000-0000-0000-000000000001")
        assert req.order_id is not None

    def test_retry_valid(self):
        req = RetryPaymentRequest(payment_method="jazzcash")
        assert req.payment_method == "jazzcash"

    def test_retry_invalid_method(self):
        with pytest.raises(ValidationError):
            RetryPaymentRequest(payment_method="bitcoin")

    def test_refund_valid(self):
        req = RefundRequest(amount=500, reason="Customer returned item")
        assert req.amount == 500

    def test_refund_zero_amount(self):
        with pytest.raises(ValidationError):
            RefundRequest(amount=0, reason="test reason here")

    def test_refund_short_reason(self):
        with pytest.raises(ValidationError):
            RefundRequest(amount=500, reason="bad")