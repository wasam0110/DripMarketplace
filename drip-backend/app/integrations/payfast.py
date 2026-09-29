# LEGACY ADAPTER: verified and corrected — see Task 3 notes.
# PAYFAST_ENABLED remains false until sandbox credentials have been confirmed
# against the live PayFast Pakistan IPN flow.
"""
app/integrations/payfast.py
────────────────────────────
PayFast Pakistan payment gateway adapter.

Docs:    https://developers.payfast.com.pk/
Sandbox: https://sandbox.payfast.com.pk
Live:    https://www.payfast.com.pk

Flow
────
1. Backend calls build_checkout_payload() → returns signed dict.
2. Frontend POSTs that dict to base_url (PayFast hosted checkout).
3. PayFast POSTs an IPN to /api/v1/payments/callback/payfast.
4. Backend calls parse_ipn() to verify signature and extract result.
5. If payment is missed/delayed, call check_status() to reconcile.

REQUIRES_LIVE_VERIFICATION items are marked with that tag.
They are correct to the best of available documentation but must be
confirmed against a real PayFast sandbox before PAYFAST_ENABLED = true.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
from decimal import Decimal, InvalidOperation
from typing import Any

import httpx

logger = logging.getLogger(__name__)

SANDBOX_URL = "https://sandbox.payfast.com.pk/api/order/request"
LIVE_URL    = "https://www.payfast.com.pk/api/order/request"

# REQUIRES_LIVE_VERIFICATION: confirm the status endpoint path with PayFast Pakistan.
SANDBOX_STATUS_URL = "https://sandbox.payfast.com.pk/api/order/status"
LIVE_STATUS_URL    = "https://www.payfast.com.pk/api/order/status"

# PayFast IPN status values → internal status names.
_STATUS_MAP: dict[str, str] = {
    "PAID":     "completed",
    "FAILED":   "failed",
    "REFUNDED": "refunded",
    "PENDING":  "pending",
}

# Statuses the IPN callback is allowed to deliver.
# "refunded" is a valid PayFast IPN status (e.g. chargebacks) — excluding it
# caused the previous version to crash with ValueError on any refund IPN.
_ACCEPTED_STATUSES = frozenset({"completed", "failed", "pending", "refunded"})


class PayFastClient:
    def __init__(
        self,
        merchant_id: str,
        secured_key: str,
        sandbox:     bool = True,
    ) -> None:
        self.merchant_id = merchant_id
        self.secured_key = secured_key
        self.sandbox     = sandbox
        self.base_url    = SANDBOX_URL if sandbox else LIVE_URL
        self.status_url  = SANDBOX_STATUS_URL if sandbox else LIVE_STATUS_URL

    # ── Signature ──────────────────────────────────────────────────────────────

    def _sign(self, params: dict[str, str]) -> str:
        """
        HMAC-SHA256 over alphabetically sorted key=value pairs, joined by '&'.
        Empty values and the 'signature' field itself are excluded from signing.

        REQUIRES_LIVE_VERIFICATION: confirm sort order, encoding and excluded
        fields against the PayFast Pakistan sandbox integration guide.
        """
        body = "&".join(
            f"{k}={v}"
            for k, v in sorted(params.items())
            if k != "signature" and v not in (None, "")
        )
        return hmac.new(
            self.secured_key.encode(),
            body.encode(),
            hashlib.sha256,
        ).hexdigest()

    # ── Checkout initiation ───────────────────────────────────────────────────

    def build_checkout_payload(
        self,
        *,
        order_id:       str,
        amount:         Decimal,
        description:    str,
        return_url:     str,
        cancel_url:     str,
        ipn_url:        str,
        customer_email: str = "",
        customer_name:  str = "",
    ) -> dict[str, str]:
        """
        Build the signed form payload that the frontend POSTs to PayFast's
        hosted checkout page.

        amount must be in PKR rupees (not paisa).
        Returns a dict that the frontend submits to self.base_url.
        """
        params: dict[str, str] = {
            "merchant_id": self.merchant_id,
            "order_id":    order_id,
            "currency":    "PKR",
            "amount":      f"{amount:.2f}",
            "description": description[:255],
            "return_url":  return_url,
            "cancel_url":  cancel_url,
            "ipn_url":     ipn_url,
        }
        if customer_email:
            params["customer_email"] = customer_email
        if customer_name:
            params["customer_name"] = customer_name[:100]

        params["signature"] = self._sign(params)
        return params

    # ── IPN handling ──────────────────────────────────────────────────────────

    def verify_ipn(self, payload: dict[str, str]) -> bool:
        """Verify the HMAC signature on an IPN callback from PayFast."""
        received = payload.get("signature", "")
        expected = self._sign(payload)
        return hmac.compare_digest(received, expected)

    def parse_ipn(self, payload: dict[str, Any]) -> dict[str, Any]:
        """
        Verify and parse a PayFast IPN callback.

        Returns a normalised dict:
          {
            "order_id":  str,
            "status":    "completed" | "failed" | "pending" | "refunded",
            "amount":    Decimal,          # PKR rupees
            "currency":  str,
            "txn_id":    str,
            "raw":       dict,
          }

        Raises ValueError on signature failure, unsupported status, or
        invalid amount.
        """
        if not self.merchant_id or not self.secured_key:
            raise ValueError("PayFast is not configured")

        str_payload = {k: str(v) for k, v in payload.items()}
        if not self.verify_ipn(str_payload):
            raise ValueError("PayFast IPN signature verification failed")

        raw_status = str(payload.get("payment_status", "")).upper()
        status     = _STATUS_MAP.get(raw_status)

        if status not in _ACCEPTED_STATUSES:
            raise ValueError(
                f"Unsupported PayFast IPN status: {raw_status!r}. "
                f"Expected one of {sorted(_STATUS_MAP)}"
            )

        try:
            amount = Decimal(str(payload.get("amount", "0")))
            if not amount.is_finite() or amount <= 0:
                raise ValueError("amount must be a positive finite number")
        except InvalidOperation as exc:
            raise ValueError(
                f"Invalid IPN amount: {payload.get('amount')!r}"
            ) from exc

        return {
            "order_id": str(payload.get("order_id", "")),
            "status":   status,
            "amount":   amount,
            "currency": str(payload.get("currency", "")),
            "txn_id":   str(payload.get("transaction_id", "")),
            "raw":      dict(payload),
        }

    # ── Reconciliation ────────────────────────────────────────────────────────

    async def check_status(self, order_id: str) -> dict[str, Any]:
        """
        Query PayFast for the current status of a payment by order_id.
        Use this when an IPN is missed or delayed to avoid an order stuck
        in pending state.

        REQUIRES_LIVE_VERIFICATION: confirm the endpoint path, request format,
        and response schema with PayFast Pakistan's developer portal before
        calling in production.

        Returns the raw JSON response from PayFast.
        Raises httpx.HTTPError on network or HTTP errors.
        """
        params: dict[str, str] = {
            "merchant_id": self.merchant_id,
            "order_id":    order_id,
        }
        params["signature"] = self._sign(params)

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(self.status_url, params=params)
            response.raise_for_status()
            return response.json()
