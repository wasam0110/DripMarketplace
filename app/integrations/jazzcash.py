from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime
from typing import Optional

import httpx

from app.core.exceptions import ExternalServiceError


class JazzCashClient:
    """
    JazzCash Mobile Wallet payment integration.
    Docs: https://sandbox.jazzcash.com.pk/ApplicationAPI/API/2.0/
    """

    SANDBOX_URL    = "https://sandbox.jazzcash.com.pk/ApplicationAPI/API/2.0/Purchase/DoMWalletTransaction"
    PRODUCTION_URL = "https://payments.jazzcash.com.pk/ApplicationAPI/API/2.0/Purchase/DoMWalletTransaction"

    SUCCESS_CODES = {"000"}   # JazzCash success response codes

    def __init__(
        self,
        merchant_id:     str,
        password:        str,
        integrity_salt:  str,
        sandbox:         bool = False,
    ) -> None:
        self.merchant_id    = merchant_id
        self.password       = password
        self.integrity_salt = integrity_salt
        self.endpoint       = self.SANDBOX_URL if sandbox else self.PRODUCTION_URL

    # ── Hash ──────────────────────────────────────────────────────────────────

    def build_secure_hash(self, params: dict) -> str:
        """
        SecureHash = HMAC-SHA256(integrity_salt&sorted_params, integrity_salt)
        JazzCash spec: sort params by key, join with '&', prepend integrity_salt&
        """
        filtered   = {k: v for k, v in params.items() if k != "pp_SecureHash" and v != ""}
        sorted_str = "&".join(f"{k}={v}" for k, v in sorted(filtered.items()))
        data       = self.integrity_salt + "&" + sorted_str
        return hmac.new(
            self.integrity_salt.encode("utf-8"),
            data.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest().upper()

    def verify_callback(self, form_data: dict) -> bool:
        """Verify the pp_SecureHash in the callback."""
        received   = form_data.get("pp_SecureHash", "")
        params     = {k: v for k, v in form_data.items() if k != "pp_SecureHash"}
        computed   = self.build_secure_hash(params)
        return hmac.compare_digest(received.upper(), computed.upper())

    def is_success(self, response_code: str) -> bool:
        return response_code in self.SUCCESS_CODES

    # ── Initiate ──────────────────────────────────────────────────────────────

    async def initiate_wallet_payment(
        self,
        order_number: str,
        amount_pkr:   int,
        mobile:       str,
        description:  str = "DRIP Marketplace",
    ) -> dict:
        """
        Initiate JazzCash wallet transaction.
        Returns: {txn_ref, response_code, payment_url, raw}
        """
        txn_ref = f"T{datetime.utcnow().strftime('%Y%m%d%H%M%S')}{order_number[-6:].upper()}"
        txn_dt  = datetime.utcnow().strftime("%Y%m%d%H%M%S")

        params = {
            "pp_Amount":        str(amount_pkr * 100),  # JazzCash uses paisa
            "pp_BillReference": order_number,
            "pp_Description":   description,
            "pp_Language":      "EN",
            "pp_MerchantID":    self.merchant_id,
            "pp_MobileNumber":  mobile,
            "pp_Password":      self.password,
            "pp_ReturnURL":     "",
            "pp_TxnCurrency":   "PKR",
            "pp_TxnDateTime":   txn_dt,
            "pp_TxnExpiryDateTime": txn_dt,
            "pp_TxnRefNo":      txn_ref,
            "pp_TxnType":       "MWALLET",
            "pp_Version":       "1.1",
        }
        params["pp_SecureHash"] = self.build_secure_hash(params)

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.post(self.endpoint, json=params)
                data = r.json()
        except httpx.HTTPError as e:
            raise ExternalServiceError(f"JazzCash unreachable: {e}") from e

        return {
            "txn_ref":       txn_ref,
            "response_code": data.get("pp_ResponseCode", ""),
            "payment_url":   data.get("pp_PayURL"),
            "raw":           data,
        }