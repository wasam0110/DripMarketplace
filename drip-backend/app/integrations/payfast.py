# LEGACY ADAPTER: merchant protocol has not been independently verified.
# Disabled by PAYFAST_ENABLED by default. See BACKEND_HANDOFF.md before enabling.
"""
app/integrations/payfast.py
────────────────────────────
PayFast Pakistan payment gateway integration.

Docs: https://developers.payfast.com.pk/

Flow:
  1. Backend builds a signed form payload → returns to frontend
  2. Frontend POSTs the form to PayFast hosted checkout page
  3. PayFast POSTs IPN (Instant Payment Notification) to /payments/callback/payfast
  4. Backend verifies signature, updates order status

Sandbox: https://sandbox.payfast.com.pk
Live:    https://www.payfast.com.pk
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
import hashlib
import hmac
import logging
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlencode

logger = logging.getLogger(__name__)

SANDBOX_URL = "https://sandbox.payfast.com.pk/api/order/request"
LIVE_URL    = "https://www.payfast.com.pk/api/order/request"


class PayFastClient:
    def __init__(
        self,
        merchant_id:  str,
        secured_key:  str,
        sandbox:      bool = True,
    ) -> None:
        self.merchant_id = merchant_id
        self.secured_key = secured_key
        self.sandbox     = sandbox
        self.base_url    = SANDBOX_URL if sandbox else LIVE_URL

    # ── Signature ──────────────────────────────────────────────────────────────

    def _sign(self, params: dict[str, str]) -> str:
        """
        PayFast signature: HMAC-SHA256 over the sorted, encoded payload
        using the merchant's secured_key.
        """
        sorted_params = "&".join(
            f"{k}={v}"
            for k, v in sorted(params.items())
            if k != "signature" and v not in (None, "")
        )
        return hmac.new(
            self.secured_key.encode(),
            sorted_params.encode(),
            hashlib.sha256,
        ).hexdigest()

    def verify_ipn(self, payload: dict[str, Any]) -> bool:
        """Verify the IPN callback signature from PayFast."""
        received_sig = payload.get("signature", "")
        expected_sig = self._sign({k: str(v) for k, v in payload.items()})
        return hmac.compare_digest(received_sig, expected_sig)

    # ── Payment initiation ────────────────────────────────────────────────────

    def build_checkout_payload(
        self,
        *,
        order_id:    str,
        amount:      int,           # in PKR (whole rupees, NOT paisa)
        description: str,
        return_url:  str,
        cancel_url:  str,
        ipn_url:     str,
        customer_email: str = "",
        customer_name:  str = "",
    ) -> dict[str, str]:
        """
        Build the signed form payload to redirect the customer to PayFast.
        Returns a dict that the frontend can POST to self.base_url.

        Amount is in PKR rupees (PayFast expects rupees, not paisa).
        """
        params: dict[str, str] = {
            "merchant_id":    self.merchant_id,
            "order_id":       order_id,
            "currency":       "PKR",
            "amount":         format(Decimal(amount), ".2f"),
            "description":    description[:255],
            "return_url":     return_url,
            "cancel_url":     cancel_url,
            "ipn_url":        ipn_url,
        }
        if customer_email:
            params["customer_email"] = customer_email
        if customer_name:
            params["customer_name"]  = customer_name[:100]

        params["signature"] = self._sign(params)
        return params

    # ── IPN handling ──────────────────────────────────────────────────────────

    def parse_ipn(self, payload: dict[str, Any]) -> dict[str, Any]:
        """
        Parse and verify an IPN callback from PayFast.

        Returns a normalised dict:
          {
            "order_id":    str,
            "status":      "completed" | "failed" | "refunded",
            "amount":      int,  # PKR
            "txn_id":      str,
            "raw":         dict,
          }

        Raises ValueError if the signature is invalid.
        """
        if not self.merchant_id or not self.secured_key:
            raise ValueError("PayFast is not configured")
        if not self.verify_ipn({k: str(v) for k, v in payload.items()}):
            raise ValueError("PayFast IPN signature verification failed")

        status_map = {
            "PAID":     "completed",
            "FAILED":   "failed",
            "REFUNDED": "refunded",
            "PENDING":  "pending",
        }
        raw_status = str(payload.get("payment_status", "")).upper()
        status     = status_map.get(raw_status)
        if status not in ("completed", "failed", "pending"):
            raise ValueError("Unsupported payment notification status")
        try:
            amount = Decimal(str(payload.get("amount", "0")))
            if not amount.is_finite() or amount <= 0:
                raise ValueError("Invalid payment amount")
        except InvalidOperation as exc:
            raise ValueError("Invalid payment amount") from exc

        return {
            "order_id": str(payload.get("order_id", "")),
            "status":   status,
            "amount":   Decimal(str(payload.get("amount", "0"))),
            "currency": str(payload.get("currency", "")),
            "txn_id":   str(payload.get("transaction_id", "")),
            "raw":      dict(payload),
        }
