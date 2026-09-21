"""
app/core/exceptions.py
──────────────────────
Custom exception hierarchy for DRIP.

Design rules:
  • Every exception maps to exactly one HTTP status code.
  • User-facing messages are generic (no internal details).
  • Developer details go to logs, never to API responses.
  • The global exception handler in main.py catches all DRIPException subclasses.
"""

from __future__ import annotations

from typing import Any


# ── Base ──────────────────────────────────────────────────────────────────────

class DRIPException(Exception):
    """Base class for all DRIP application exceptions."""

    http_status: int = 400
    default_code: str = "ERROR"
    default_message: str = "An error occurred."

    def __init__(
        self,
        message: str | None = None,
        code: str | None = None,
        fields: dict[str, str] | None = None,
        detail: str | None = None,        # Internal detail — logs only, never sent to client
    ) -> None:
        self.message = message or self.default_message
        self.code    = code    or self.default_code
        self.fields  = fields  or {}
        self.detail  = detail  # e.g. repr(original_exception)
        super().__init__(self.message)

    def to_response(self, request_id: str | None = None) -> dict[str, Any]:
        """Safe representation for the API response body."""
        body: dict[str, Any] = {
            "error": {
                "code":    self.code,
                "message": self.message,
            }
        }
        if self.fields:
            body["error"]["fields"] = self.fields
        if request_id:
            body["error"]["request_id"] = request_id
        return body


# ── 400 Bad Request ───────────────────────────────────────────────────────────

class ValidationError(DRIPException):
    """Request body or query param failed validation."""
    http_status   = 422
    default_code  = "VALIDATION_ERROR"
    default_message = "Request validation failed. Please check the highlighted fields."

    def __init__(self, fields: dict[str, str]) -> None:
        super().__init__(
            message=self.default_message,
            code=self.default_code,
            fields=fields,
        )


class BusinessRuleError(DRIPException):
    """Request is structurally valid but violates a business rule."""
    http_status   = 422
    default_code  = "BUSINESS_RULE_VIOLATION"
    default_message = "This action is not permitted."


# ── 401 Unauthorized ──────────────────────────────────────────────────────────

class AuthenticationError(DRIPException):
    http_status   = 401
    default_code  = "UNAUTHORIZED"
    default_message = "Authentication required."


class InvalidCredentialsError(AuthenticationError):
    default_code    = "INVALID_CREDENTIALS"
    default_message = "Invalid email or password."


class TokenExpiredError(AuthenticationError):
    default_code    = "TOKEN_EXPIRED"
    default_message = "Your session has expired. Please log in again."


class TokenInvalidError(AuthenticationError):
    default_code    = "TOKEN_INVALID"
    default_message = "Invalid authentication token."


class EmailNotVerifiedError(AuthenticationError):
    default_code    = "EMAIL_NOT_VERIFIED"
    default_message = "Please verify your email address before logging in."


class TwoFactorRequiredError(AuthenticationError):
    default_code    = "2FA_REQUIRED"
    default_message = "Two-factor authentication code is required for this account."


class TwoFactorInvalidError(AuthenticationError):
    default_code    = "2FA_INVALID"
    default_message = "Invalid two-factor authentication code."


# ── 403 Forbidden ─────────────────────────────────────────────────────────────

class PermissionDeniedError(DRIPException):
    http_status   = 403
    default_code  = "FORBIDDEN"
    default_message = "You do not have permission to perform this action."


class SellerSuspendedError(PermissionDeniedError):
    default_code    = "SELLER_SUSPENDED"
    default_message = "This seller account has been suspended."


class SellerNotActiveError(PermissionDeniedError):
    default_code    = "SELLER_NOT_ACTIVE"
    default_message = "Seller account is not yet active."


# ── 404 Not Found ─────────────────────────────────────────────────────────────

class NotFoundError(DRIPException):
    http_status   = 404
    default_code  = "NOT_FOUND"
    default_message = "The requested resource was not found."

    def __init__(self, resource: str = "Resource", resource_id: str | None = None) -> None:
        msg = f"{resource} not found."
        if resource_id:
            msg = f"{resource} '{resource_id}' not found."
        super().__init__(message=msg, code=self.default_code)


# ── 409 Conflict ──────────────────────────────────────────────────────────────

class ConflictError(DRIPException):
    http_status   = 409
    default_code  = "CONFLICT"
    default_message = "This resource already exists."


class DuplicateEmailError(ConflictError):
    default_code    = "DUPLICATE_EMAIL"
    default_message = "An account with this email address already exists."


class DuplicateBrandNameError(ConflictError):
    default_code    = "DUPLICATE_BRAND_NAME"
    default_message = "A brand with this name already exists."


class DuplicateSkuError(ConflictError):
    default_code    = "DUPLICATE_SKU"
    default_message = "A product variant with this SKU already exists."


class DuplicateReviewError(ConflictError):
    default_code    = "DUPLICATE_REVIEW"
    default_message = "You have already reviewed this product."


# ── 422 Business Logic ────────────────────────────────────────────────────────

class InsufficientStockError(BusinessRuleError):
    default_code    = "INSUFFICIENT_STOCK"
    default_message = "One or more items in your cart are out of stock."

    def __init__(self, product_name: str | None = None, variant_label: str | None = None) -> None:
        msg = self.default_message
        if product_name:
            label = f" ({variant_label})" if variant_label else ""
            msg = f"'{product_name}{label}' does not have enough stock."
        super().__init__(message=msg)


class NoSlotsAvailableError(BusinessRuleError):
    default_code    = "NO_SLOTS_AVAILABLE"
    default_message = "No product slots available. Purchase extra slots at PKR 50 each."


class InvalidStatusTransitionError(BusinessRuleError):
    default_code    = "INVALID_STATUS_TRANSITION"

    def __init__(self, from_status: str, to_status: str) -> None:
        super().__init__(
            message=f"Cannot transition from '{from_status}' to '{to_status}'.",
            code=self.default_code,
        )


class OrderCancellationError(BusinessRuleError):
    default_code    = "ORDER_CANNOT_BE_CANCELLED"
    default_message = "This order cannot be cancelled at its current stage."


class InsufficientBalanceError(BusinessRuleError):
    default_code    = "INSUFFICIENT_BALANCE"
    default_message = "Insufficient available balance for this withdrawal."


class CouponInvalidError(BusinessRuleError):
    default_code    = "COUPON_INVALID"
    default_message = "This coupon code is invalid or has expired."


class CouponLimitReachedError(BusinessRuleError):
    default_code    = "COUPON_LIMIT_REACHED"
    default_message = "This coupon has reached its usage limit."


class PaymentVerificationError(BusinessRuleError):
    """Payment callback HMAC verification failed — potential tampering."""
    default_code    = "PAYMENT_VERIFICATION_FAILED"
    default_message = "Payment verification failed."


class CODLimitExceededError(BusinessRuleError):
    default_code    = "COD_LIMIT_EXCEEDED"
    default_message = f"Cash on Delivery is not available for orders above a certain amount."


# ── 429 Rate Limited ──────────────────────────────────────────────────────────

class RateLimitError(DRIPException):
    http_status   = 429
    default_code  = "RATE_LIMITED"
    default_message = "Too many requests. Please wait a moment and try again."

    def __init__(self, retry_after_seconds: int = 60) -> None:
        super().__init__(message=self.default_message, code=self.default_code)
        self.retry_after = retry_after_seconds


# ── 500 Server Error ──────────────────────────────────────────────────────────

class ServerError(DRIPException):
    http_status   = 500
    default_code  = "INTERNAL_ERROR"
    default_message = "An unexpected error occurred. Our team has been notified."


class DatabaseError(ServerError):
    default_code    = "DATABASE_ERROR"
    default_message = "A database error occurred. Please try again."


class StorageError(ServerError):
    default_code    = "STORAGE_ERROR"
    default_message = "File storage operation failed. Please try again."


class PaymentGatewayError(ServerError):
    default_code    = "PAYMENT_GATEWAY_ERROR"
    default_message = "Payment gateway is unavailable. Please try a different payment method."


class PaymentRequiredError(BusinessRuleError):
    status_code = 402
    error_code  = "payment_required"
    message     = "Payment is required to complete this action"
class ExternalServiceError(DRIPException):
    http_status     = 502
    default_code    = "EXTERNAL_SERVICE_ERROR"
    default_message = "An upstream service is unavailable"