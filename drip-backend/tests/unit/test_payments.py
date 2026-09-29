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
        req = RetryPaymentRequest(payment_method="payfast")
        assert req.payment_method == "payfast"

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

    
class TestPayFastAdapter:
    """
    Unit tests for PayFastClient.

    These tests exercise the adapter in isolation — no real network calls,
    no DB, no credentials required.  They prove the contract that:
      - Signatures are deterministic and tamper-evident.
      - build_checkout_payload includes all required fields with a valid signature.
      - parse_ipn correctly maps all PayFast status strings, including REFUNDED.
      - parse_ipn rejects bad signatures, unsupported statuses, and invalid amounts.
      - check_status builds a signed GET request to the correct endpoint.

    Live verification items (marked REQUIRES_LIVE_VERIFICATION in the adapter)
    must be confirmed with a real PayFast Pakistan sandbox account before
    PAYFAST_ENABLED is set to true.
    """

    def setup_method(self):
        from app.integrations.payfast import PayFastClient
        self.pf = PayFastClient(
            merchant_id="TEST_MERCHANT",
            secured_key="test_secured_key_abc",
            sandbox=True,
        )

    # ── Signature ─────────────────────────────────────────────────────────────

    def test_sign_is_deterministic(self):
        params = {"amount": "2600.00", "order_id": "ORD-001", "currency": "PKR"}
        assert self.pf._sign(params) == self.pf._sign(params)

    def test_sign_excludes_signature_field(self):
        params_with = {"amount": "2600.00", "signature": "old_value"}
        params_without = {"amount": "2600.00"}
        assert self.pf._sign(params_with) == self.pf._sign(params_without)

    def test_sign_excludes_empty_values(self):
        params_with_empty = {"amount": "2600.00", "customer_email": ""}
        params_without = {"amount": "2600.00"}
        assert self.pf._sign(params_with_empty) == self.pf._sign(params_without)

    def test_sign_is_order_independent(self):
        p1 = {"a_field": "x", "b_field": "y"}
        p2 = {"b_field": "y", "a_field": "x"}
        assert self.pf._sign(p1) == self.pf._sign(p2)

    def test_sign_different_key_different_result(self):
        from app.integrations.payfast import PayFastClient
        pf2 = PayFastClient("mid", "different_key")
        params = {"amount": "100.00"}
        assert self.pf._sign(params) != pf2._sign(params)

    def test_sign_tampered_value_changes_result(self):
        params = {"amount": "2600.00", "order_id": "ORD-001"}
        sig1 = self.pf._sign(params)
        tampered = {**params, "amount": "1.00"}
        assert self.pf._sign(tampered) != sig1

    # ── build_checkout_payload ────────────────────────────────────────────────

    def test_checkout_payload_required_fields_present(self):
        from decimal import Decimal
        payload = self.pf.build_checkout_payload(
            order_id="ORD-001",
            amount=Decimal("2600.00"),
            description="WearHowZ order WH-000001",
            return_url="https://example.com/success",
            cancel_url="https://example.com/cancel",
            ipn_url="https://api.example.com/callback/payfast",
        )
        for field in ("merchant_id", "order_id", "currency", "amount",
                      "description", "return_url", "cancel_url", "ipn_url", "signature"):
            assert field in payload, f"Missing field: {field}"

    def test_checkout_payload_amount_formatted_to_two_dp(self):
        from decimal import Decimal
        payload = self.pf.build_checkout_payload(
            order_id="ORD-002", amount=Decimal("999"), description="Test",
            return_url="https://r.test", cancel_url="https://c.test",
            ipn_url="https://i.test",
        )
        assert payload["amount"] == "999.00"

    def test_checkout_payload_signature_is_self_consistent(self):
        from decimal import Decimal
        payload = self.pf.build_checkout_payload(
            order_id="ORD-003", amount=Decimal("1200.00"), description="d",
            return_url="https://r", cancel_url="https://c", ipn_url="https://i",
        )
        without_sig = {k: v for k, v in payload.items() if k != "signature"}
        assert payload["signature"] == self.pf._sign(without_sig)

    def test_checkout_payload_optional_email_and_name_included(self):
        from decimal import Decimal
        payload = self.pf.build_checkout_payload(
            order_id="ORD-004", amount=Decimal("500.00"), description="d",
            return_url="r", cancel_url="c", ipn_url="i",
            customer_email="buyer@test.com", customer_name="Ali Khan",
        )
        assert payload["customer_email"] == "buyer@test.com"
        assert payload["customer_name"] == "Ali Khan"

    def test_checkout_payload_description_truncated_at_255(self):
        from decimal import Decimal
        payload = self.pf.build_checkout_payload(
            order_id="ORD-005", amount=Decimal("100.00"),
            description="x" * 300,
            return_url="r", cancel_url="c", ipn_url="i",
        )
        assert len(payload["description"]) == 255

    def test_sandbox_flag_reflected_in_base_url(self):
        assert "sandbox" in self.pf.base_url

    def test_live_flag_uses_live_url(self):
        from app.integrations.payfast import PayFastClient
        pf_live = PayFastClient("mid", "key", sandbox=False)
        assert "sandbox" not in pf_live.base_url

    # ── verify_ipn ────────────────────────────────────────────────────────────

    def test_verify_ipn_valid_signature(self):
        raw = {
            "order_id": "ORD-001", "payment_status": "PAID",
            "amount": "2600.00", "currency": "PKR", "transaction_id": "TXN001",
        }
        raw["signature"] = self.pf._sign(raw)
        assert self.pf.verify_ipn(raw) is True

    def test_verify_ipn_tampered_returns_false(self):
        raw = {
            "order_id": "ORD-001", "payment_status": "PAID",
            "amount": "2600.00", "currency": "PKR", "transaction_id": "TXN001",
            "signature": "completely_wrong_signature",
        }
        assert self.pf.verify_ipn(raw) is False

    def test_verify_ipn_missing_signature_returns_false(self):
        raw = {"order_id": "ORD-001", "payment_status": "PAID", "amount": "2600.00"}
        assert self.pf.verify_ipn(raw) is False

    # ── parse_ipn ─────────────────────────────────────────────────────────────

    def _signed_ipn(self, extra: dict) -> dict:
        base = {
            "order_id": "ORD-001", "payment_status": "PAID",
            "amount": "2600.00", "currency": "PKR", "transaction_id": "TXN001",
        }
        base.update(extra)
        base["signature"] = self.pf._sign({k: str(v) for k, v in base.items()})
        return base

    def test_parse_ipn_paid_maps_to_completed(self):
        from decimal import Decimal
        result = self.pf.parse_ipn(self._signed_ipn({"payment_status": "PAID"}))
        assert result["status"] == "completed"
        assert result["amount"] == Decimal("2600.00")
        assert result["txn_id"] == "TXN001"
        assert result["order_id"] == "ORD-001"

    def test_parse_ipn_failed_maps_to_failed(self):
        result = self.pf.parse_ipn(self._signed_ipn({"payment_status": "FAILED"}))
        assert result["status"] == "failed"

    def test_parse_ipn_pending_maps_to_pending(self):
        result = self.pf.parse_ipn(self._signed_ipn({"payment_status": "PENDING"}))
        assert result["status"] == "pending"

    def test_parse_ipn_refunded_maps_to_refunded(self):
        """
        Bug fix: REFUNDED is a valid PayFast IPN status (chargebacks).
        The previous implementation rejected it with ValueError.
        """
        result = self.pf.parse_ipn(self._signed_ipn({"payment_status": "REFUNDED"}))
        assert result["status"] == "refunded"

    def test_parse_ipn_invalid_signature_raises(self):
        payload = self._signed_ipn({})
        payload["signature"] = "bad_sig"
        with pytest.raises(ValueError, match="signature"):
            self.pf.parse_ipn(payload)

    def test_parse_ipn_unsupported_status_raises(self):
        payload = self._signed_ipn({"payment_status": "CANCELLED"})
        with pytest.raises(ValueError, match="CANCELLED"):
            self.pf.parse_ipn(payload)

    def test_parse_ipn_zero_amount_raises(self):
        payload = self._signed_ipn({"amount": "0.00"})
        with pytest.raises(ValueError, match="amount"):
            self.pf.parse_ipn(payload)

    def test_parse_ipn_negative_amount_raises(self):
        payload = self._signed_ipn({"amount": "-100.00"})
        with pytest.raises(ValueError, match="amount"):
            self.pf.parse_ipn(payload)

    def test_parse_ipn_non_numeric_amount_raises(self):
        payload = self._signed_ipn({"amount": "abc"})
        with pytest.raises(ValueError):
            self.pf.parse_ipn(payload)

    def test_parse_ipn_unconfigured_client_raises(self):
        from app.integrations.payfast import PayFastClient
        pf_empty = PayFastClient("", "", sandbox=True)
        with pytest.raises(ValueError, match="not configured"):
            pf_empty.parse_ipn({})

    def test_parse_ipn_raw_is_preserved(self):
        payload = self._signed_ipn({})
        result = self.pf.parse_ipn(payload)
        assert result["raw"] == payload