from __future__ import annotations

import hashlib
import hmac
from datetime import datetime

import httpx

from app.core.exceptions import ExternalServiceError


class EasypaisaClient:
    """
    Easypaisa payment integration.
    Docs: https://developer.easypaisa.com.pk/
    """

    SANDBOX_URL    = "https://easypaisa.com.pk/tpg/"
    PRODUCTION_URL = "https://easypaisa.com.pk/tpg/"

    SUCCESS_CODES  = {"0000"}

    def __init__(
        self,
        store_id:   str,
        store_key:  str,
        account_no: str,
        sandbox:    bool = False,
    ) -> None:
        self.store_id   = store_id
        self.store_key  = store_key
        self.account_no = account_no
        self.endpoint   = self.SANDBOX_URL if sandbox else self.PRODUCTION_URL

    # ── Hash ──────────────────────────────────────────────────────────────────

    def build_hash(self, params: dict) -> str:
        """
        Hash = SHA-256(sorted_values_concatenated + store_key)
        """
        sorted_vals = "".join(str(v) for _, v in sorted(params.items()))
        data        = sorted_vals + self.store_key
        return hashlib.sha256(data.encode("utf-8")).hexdigest()

    def verify_callback(self, data: dict) -> bool:
        received = data.pop("hash", "")
        computed = self.build_hash(data)
        return hmac.compare_digest(received, computed)

    def is_success(self, response_code: str) -> bool:
        return response_code in self.SUCCESS_CODES

    # ── Initiate ──────────────────────────────────────────────────────────────

    async def initiate_payment(
        self,
        order_number: str,
        amount_pkr:   int,
        email:        str = "",
    ) -> dict:
        """
        Initiate Easypaisa transaction.
        Returns: {order_ref, payment_url, raw}
        """
        order_ref = f"EP{datetime.utcnow().strftime('%Y%m%d%H%M%S')}{order_number[-4:].upper()}"

        params = {
            "orderId":         order_ref,
            "storeId":         self.store_id,
            "transactionAmount": f"{amount_pkr:.2f}",
            "mobileAccountNo": self.account_no,
            "emailAddress":    email,
            "transactionType": "InitialRequest",
            "tokenExpiry":     "",
            "bankIdentificationNumber": "",
            "encryptedHashRequest": "",
        }
        params["postBackURL"] = ""
        params["hash"] = self.build_hash({
            k: v for k, v in params.items() if k not in ("hash", "postBackURL")
        })

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.post(self.endpoint, json=params)
                data = r.json()
        except httpx.HTTPError as e:
            raise ExternalServiceError(f"Easypaisa unreachable: {e}") from e

        return {
            "order_ref":     order_ref,
            "response_code": data.get("responseCode", ""),
            "payment_url":   data.get("redirectURL"),
            "raw":           data,
        }