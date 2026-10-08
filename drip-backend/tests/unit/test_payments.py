"""Unit tests — Block 6: Payments. No DB required."""

import pytest
from pydantic import ValidationError

from app.schemas.payment import (
    InitiatePaymentRequest,
    RefundRequest,
    RetryPaymentRequest,
)


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


class TestPayFastHostedCheckout:
    def make_client(self, handler, *, sandbox=True, api_base_url=""):
        import httpx

        from app.integrations.payfast import PayFastClient

        http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        return (
            PayFastClient(
                "MERCHANT-1",
                "secret-key",
                "WearHowZ",
                sandbox,
                api_base_url=api_base_url,
                http_client=http,
            ),
            http,
        )

    @pytest.mark.asyncio
    async def test_token_request_matches_documented_form_and_returns_token(self):
        from urllib.parse import parse_qs

        import httpx

        requests = []

        def handler(request):
            requests.append(request)
            return httpx.Response(
                200, json={"MERCHANT_ID": "MERCHANT-1", "ACCESS_TOKEN": "one-time-token"}
            )

        client, http = self.make_client(handler)
        try:
            token = await client.get_checkout_token(basket_id="ORDER-1", amount=100)
        finally:
            await http.aclose()
        assert token == "one-time-token"
        assert requests[0].url.path.endswith("/GetAccessToken")
        assert parse_qs(requests[0].content.decode()) == {
            "MERCHANT_ID": ["MERCHANT-1"],
            "SECURED_KEY": ["secret-key"],
            "BASKET_ID": ["ORDER-1"],
            "TXNAMT": ["100.00"],
            "CURRENCY_CODE": ["PKR"],
        }

    @pytest.mark.asyncio
    async def test_token_response_rejects_merchant_mismatch_and_missing_token(self):
        import httpx

        from app.integrations.payfast import PayFastProtocolError

        responses = iter(
            [
                {"MERCHANT_ID": "OTHER", "ACCESS_TOKEN": "token"},
                {"MERCHANT_ID": "MERCHANT-1", "MESSAGE": "declined"},
            ]
        )
        client, http = self.make_client(lambda request: httpx.Response(200, json=next(responses)))
        try:
            with pytest.raises(PayFastProtocolError, match="merchant mismatch"):
                await client.get_checkout_token(basket_id="ORDER-1", amount=100)
            with pytest.raises(PayFastProtocolError, match="declined"):
                await client.get_checkout_token(basket_id="ORDER-1", amount=100)
        finally:
            await http.aclose()

    def test_checkout_payload_uses_documented_fields_without_secured_key(self):
        from datetime import date
        from decimal import Decimal

        import httpx

        client, http = self.make_client(lambda request: httpx.Response(500))
        payload = client.build_checkout_payload(
            token="one-time-token",
            basket_id="ORDER-1",
            amount=Decimal("2600"),
            description="WearHowZ order WH-1",
            success_url="https://shop.test/success",
            failure_url="https://shop.test/failure",
            checkout_url="https://api.test/callback",
            customer_email="Buyer@Example.com",
            customer_mobile="03001234567",
            order_date=date(2026, 10, 7),
        )
        assert payload == {
            **payload,
            "MERCHANT_ID": "MERCHANT-1",
            "MERCHANT_NAME": "WearHowZ",
            "TOKEN": "one-time-token",
            "PROCCODE": "00",
            "TXNAMT": "2600.00",
            "CUSTOMER_MOBILE_NO": "03001234567",
            "CUSTOMER_EMAIL_ADDRESS": "buyer@example.com",
            "VERSION": "WHZ-1.0",
            "TXNDESC": "WearHowZ order WH-1",
            "SUCCESS_URL": "https://shop.test/success",
            "FAILURE_URL": "https://shop.test/failure",
            "BASKET_ID": "ORDER-1",
            "ORDER_DATE": "2026-10-07",
            "CHECKOUT_URL": "https://api.test/callback",
            "CURRENCY_CODE": "PKR",
        }
        assert payload["SIGNATURE"]
        assert "SECURED_KEY" not in payload
        assert client.checkout_url.endswith("/PostTransaction")
        assert "ipguat.apps.net.pk" in client.checkout_url
        import asyncio

        asyncio.run(http.aclose())

    def test_callback_verification_success_failure_and_tampering(self):
        import httpx

        from app.integrations.payfast import PayFastProtocolError

        client, http = self.make_client(lambda request: httpx.Response(500))
        success = {
            "basket_id": "ORDER-1",
            "err_code": "000",
            "err_msg": "Approved",
            "transaction_id": "TXN-1",
        }
        success["validation_hash"] = client.callback_hash(basket_id="ORDER-1", error_code="000")
        parsed = client.parse_callback(success)
        assert parsed["status"] == "completed"
        assert parsed["amount"] is None
        failed = {**success, "err_code": "101", "err_msg": "Declined"}
        failed["validation_hash"] = client.callback_hash(basket_id="ORDER-1", error_code="101")
        assert client.parse_callback(failed)["status"] == "failed"
        with pytest.raises(PayFastProtocolError, match="validation hash"):
            client.parse_callback({**success, "validation_hash": "forged"})
        import asyncio

        asyncio.run(http.aclose())

    @pytest.mark.asyncio
    async def test_status_reconciliation_uses_bearer_token_and_basket_path(self):
        from datetime import date
        from urllib.parse import parse_qs

        import httpx

        requests = []

        def handler(request):
            requests.append(request)
            if request.url.path.endswith("/token"):
                assert parse_qs(request.content.decode())["grant_type"] == ["client_credentials"]
                return httpx.Response(200, json={"access_token": "api-token"})
            assert request.headers["Authorization"] == "Bearer api-token"
            return httpx.Response(200, json={"basket_id": "ORDER-1", "code": "00"})

        client, http = self.make_client(handler, api_base_url="https://api.test")
        try:
            result = await client.check_status(
                basket_id="ORDER-1",
                order_date=date(2026, 10, 7),
                customer_ip="203.0.113.1",
            )
        finally:
            await http.aclose()
        assert result["code"] == "00"
        assert requests[1].url.path == "/transaction/basket_id/ORDER-1"
        assert dict(requests[1].url.params) == {
            "order_date": "2026-10-07",
            "customer_ip": "203.0.113.1",
        }

    def test_live_urls_and_invalid_amount(self):
        from decimal import Decimal

        import httpx

        from app.integrations.payfast import PayFastProtocolError

        client, http = self.make_client(lambda request: httpx.Response(500), sandbox=False)
        assert "ipg1.apps.net.pk" in client.token_url
        with pytest.raises(PayFastProtocolError, match="positive"):
            client.build_checkout_payload(
                token="token",
                basket_id="ORDER-1",
                amount=Decimal("0"),
                description="x",
                success_url="https://shop.test/success",
                failure_url="https://shop.test/failure",
                checkout_url="https://api.test/callback",
                customer_email="buyer@example.com",
                customer_mobile="03001234567",
                order_date=__import__("datetime").date(2026, 10, 7),
            )
        import asyncio

        asyncio.run(http.aclose())
