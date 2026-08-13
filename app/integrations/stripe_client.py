from __future__ import annotations

import stripe
from stripe import WebhookSignature

from app.core.exceptions import ExternalServiceError, ValidationError as AppValidationError


class StripeClient:
    """
    Stripe PaymentIntent integration.
    """

    def __init__(self, secret_key: str, webhook_secret: str) -> None:
        stripe.api_key        = secret_key
        self.webhook_secret   = webhook_secret

    async def create_payment_intent(
        self,
        amount_pkr: int,
        order_id:   str,
        order_number: str,
    ) -> dict:
        """
        Create Stripe PaymentIntent.
        Returns: {client_secret, payment_intent_id}
        """
        try:
            intent = stripe.PaymentIntent.create(
                amount      = amount_pkr * 100,  # Stripe uses smallest currency unit (paisa)
                currency    = "pkr",
                description = f"DRIP Order {order_number}",
                metadata    = {"order_id": order_id, "order_number": order_number},
            )
            return {
                "client_secret":      intent.client_secret,
                "payment_intent_id":  intent.id,
            }
        except stripe.StripeError as e:
            raise ExternalServiceError(f"Stripe error: {e.user_message}") from e

    def verify_webhook(self, payload: bytes, signature: str) -> dict:
        """
        Verify Stripe webhook signature and return the event.
        Raises AppValidationError if signature is invalid.
        """
        try:
            event = stripe.Webhook.construct_event(
                payload, signature, self.webhook_secret
            )
            return dict(event)
        except stripe.SignatureVerificationError as e:
            raise AppValidationError("Invalid Stripe webhook signature") from e

    def get_payment_intent_id(self, event: dict) -> str | None:
        return event.get("data", {}).get("object", {}).get("id")

    def get_order_id_from_event(self, event: dict) -> str | None:
        return event.get("data", {}).get("object", {}).get("metadata", {}).get("order_id")