"""
app/integrations/payfast.py
────────────────────────────
PayFast Pakistan hosted-checkout adapter.

Docs: https://gopayfast.com/docs/

Flow
────
1. Backend requests a one-time access token for the exact basket and amount.
2. The client POSTs documented uppercase fields to PayFast hosted checkout.
3. PayFast calls /api/v1/payments/callback/payfast.
4. Backend verifies the documented validation hash and order invariants.
5. An admin can query PayFast status to reconcile a missed callback.

PAYFAST_ENABLED remains false until merchant-specific UAT acceptance passes.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

import httpx

# Hosted-checkout endpoints from PayFast Pakistan's merchant integration guide.
UAT_ROOT = "https://ipguat.apps.net.pk/Ecommerce/api/Transaction"
LIVE_ROOT = "https://ipg1.apps.net.pk/Ecommerce/api/Transaction"


class PayFastProtocolError(ValueError):
    """PayFast returned or supplied an invalid protocol payload."""


class PayFastClient:
    """PayFast Pakistan hosted checkout with verified callback hashing."""

    def __init__(
        self,
        merchant_id: str,
        secured_key: str,
        merchant_name: str = "WearHowZ",
        sandbox: bool = True,
        *,
        token_url: str = "",
        checkout_url: str = "",
        api_base_url: str = "",
        timeout_seconds: float = 15.0,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        root = UAT_ROOT if sandbox else LIVE_ROOT
        self.merchant_id = merchant_id.strip()
        self.secured_key = secured_key.strip()
        self.merchant_name = merchant_name.strip()
        self.sandbox = sandbox
        self.token_url = token_url.strip() or f"{root}/GetAccessToken"
        self.checkout_url = checkout_url.strip() or f"{root}/PostTransaction"
        self.api_base_url = api_base_url.strip().rstrip("/")
        self.timeout_seconds = timeout_seconds
        self._http_client = http_client

    @property
    def base_url(self) -> str:
        """Compatibility alias used by the payment response schema."""
        return self.checkout_url

    def _ensure_configured(self) -> None:
        if not self.merchant_id or not self.secured_key or not self.merchant_name:
            raise PayFastProtocolError("PayFast is not configured")

    async def _post_form(self, url: str, data: dict[str, str]) -> httpx.Response:
        if self._http_client is not None:
            response = await self._http_client.post(url, data=data)
        else:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(url, data=data)
        response.raise_for_status()
        return response

    async def _get(
        self, url: str, *, headers: dict[str, str], params: dict[str, str] | None = None
    ) -> httpx.Response:
        if self._http_client is not None:
            response = await self._http_client.get(url, headers=headers, params=params)
        else:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.get(url, headers=headers, params=params)
        response.raise_for_status()
        return response

    async def get_checkout_token(self, *, basket_id: str, amount: Decimal) -> str:
        """Request a one-time token server-side; never expose the secured key."""
        self._ensure_configured()
        response = await self._post_form(
            self.token_url,
            {
                "MERCHANT_ID": self.merchant_id,
                "SECURED_KEY": self.secured_key,
                "BASKET_ID": basket_id,
                "TXNAMT": _format_amount(amount),
                "CURRENCY_CODE": "PKR",
            },
        )
        try:
            payload = response.json()
        except ValueError as exc:
            raise PayFastProtocolError("PayFast token response was not JSON") from exc
        if not isinstance(payload, dict):
            raise PayFastProtocolError("PayFast token response was not an object")
        token = str(payload.get("ACCESS_TOKEN") or payload.get("access_token") or "").strip()
        returned_merchant = str(
            payload.get("MERCHANT_ID") or payload.get("merchant_id") or self.merchant_id
        ).strip()
        if returned_merchant != self.merchant_id:
            raise PayFastProtocolError("PayFast token response merchant mismatch")
        if not token:
            message = payload.get("MESSAGE") or payload.get("message") or "token missing"
            raise PayFastProtocolError(f"PayFast token request failed: {message}")
        return token

    def build_checkout_payload(
        self,
        *,
        token: str,
        basket_id: str,
        amount: Decimal,
        description: str,
        success_url: str,
        failure_url: str,
        checkout_url: str,
        customer_email: str,
        customer_mobile: str,
        order_date: date,
    ) -> dict[str, str]:
        """Build the documented uppercase form POST for hosted checkout."""
        self._ensure_configured()
        if not token.strip():
            raise PayFastProtocolError("PayFast checkout token is required")
        if not customer_email.strip() or not customer_mobile.strip():
            raise PayFastProtocolError("Customer email and mobile number are required")
        return {
            "MERCHANT_ID": self.merchant_id,
            "MERCHANT_NAME": self.merchant_name,
            "TOKEN": token.strip(),
            "PROCCODE": "00",
            "TXNAMT": _format_amount(amount),
            "CUSTOMER_MOBILE_NO": customer_mobile.strip(),
            "CUSTOMER_EMAIL_ADDRESS": customer_email.strip().lower(),
            "SIGNATURE": secrets.token_urlsafe(24),
            "VERSION": "WHZ-1.0",
            "TXNDESC": description.strip()[:255],
            "SUCCESS_URL": success_url,
            "FAILURE_URL": failure_url,
            "BASKET_ID": basket_id,
            "ORDER_DATE": order_date.isoformat(),
            "CHECKOUT_URL": checkout_url,
            "CURRENCY_CODE": "PKR",
        }

    def callback_hash(self, *, basket_id: str, error_code: str) -> str:
        """Compute SHA-256(basket|secured-key|merchant|error-code)."""
        source = f"{basket_id}|{self.secured_key}|{self.merchant_id}|{error_code}"
        return hashlib.sha256(source.encode()).hexdigest()

    def parse_callback(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Verify and normalize a hosted-checkout redirect/IPN notification."""
        self._ensure_configured()
        normalized = {str(key).lower(): str(value) for key, value in payload.items()}
        basket_id = normalized.get("basket_id", "").strip()
        error_code = normalized.get("err_code", "").strip()
        received_hash = normalized.get("validation_hash", "").strip().lower()
        transaction_id = normalized.get("transaction_id", "").strip()
        if not basket_id or not error_code or not received_hash or not transaction_id:
            raise PayFastProtocolError("PayFast callback is missing required fields")
        expected_hash = self.callback_hash(basket_id=basket_id, error_code=error_code)
        if not hmac.compare_digest(received_hash, expected_hash):
            raise PayFastProtocolError("PayFast callback validation hash failed")

        amount: Decimal | None = None
        amount_value = normalized.get("txnamt") or normalized.get("amount")
        if amount_value:
            try:
                amount = Decimal(amount_value)
            except InvalidOperation as exc:
                raise PayFastProtocolError("PayFast callback amount is invalid") from exc
            if not amount.is_finite() or amount <= 0:
                raise PayFastProtocolError("PayFast callback amount is invalid")

        return {
            "order_id": basket_id,
            "status": "completed" if error_code == "000" else "failed",
            "error_code": error_code,
            "error_message": normalized.get("err_msg", "").strip(),
            "amount": amount,
            "currency": (normalized.get("currency_code") or "PKR").upper(),
            "txn_id": transaction_id,
            "payment_name": normalized.get("paymentname", "").strip(),
            "raw": dict(payload),
        }

    async def check_status(
        self,
        *,
        basket_id: str,
        order_date: date,
        customer_ip: str,
        transaction_id: str = "",
    ) -> dict[str, Any]:
        """Query PayFast's API-based status service when enabled for the merchant."""
        self._ensure_configured()
        if not self.api_base_url:
            raise PayFastProtocolError("PAYFAST_API_BASE_URL is required for reconciliation")
        token_response = await self._post_form(
            f"{self.api_base_url}/token",
            {
                "merchant_id": self.merchant_id,
                "secured_key": self.secured_key,
                "grant_type": "client_credentials",
            },
        )
        try:
            token_payload = token_response.json()
        except ValueError as exc:
            raise PayFastProtocolError("PayFast API token response was not JSON") from exc
        access_token = str(token_payload.get("access_token") or "").strip()
        if not access_token:
            raise PayFastProtocolError("PayFast API token response did not contain a token")
        if transaction_id:
            url = f"{self.api_base_url}/transaction/{transaction_id}"
            params = None
        else:
            url = f"{self.api_base_url}/transaction/basket_id/{basket_id}"
            params = {"order_date": order_date.isoformat(), "customer_ip": customer_ip}
        response = await self._get(
            url,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            params=params,
        )
        try:
            result = response.json()
        except ValueError as exc:
            raise PayFastProtocolError("PayFast status response was not JSON") from exc
        if not isinstance(result, dict):
            raise PayFastProtocolError("PayFast status response was not an object")
        return result


def _format_amount(amount: Decimal) -> str:
    value = Decimal(amount)
    if not value.is_finite() or value <= 0:
        raise PayFastProtocolError("PayFast amount must be positive and finite")
    return f"{value.quantize(Decimal('0.01')):.2f}"
