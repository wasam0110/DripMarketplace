"""
app/schemas/auth.py
────────────────────
Pydantic v2 schemas for the Auth API.
All string inputs are sanitised (stripped, lowercased where appropriate).
"""
from __future__ import annotations

import re
from datetime import datetime

from pydantic import field_validator, model_validator

from app.schemas.common import DRIPBaseModel, DRIPResponseModel

_PHONE = re.compile(r"^(\+92|0092|0)?3[0-9]{9}$")
_PWD_UPPER  = re.compile(r"[A-Z]")
_PWD_LOWER  = re.compile(r"[a-z]")
_PWD_DIGIT  = re.compile(r"[0-9]")


# ── Requests ──────────────────────────────────────────────────────────────────

class RegisterRequest(DRIPBaseModel):
    first_name: str
    last_name:  str
    email:      str
    password:   str
    phone:      str | None = None

    @field_validator("email")
    @classmethod
    def normalise_email(cls, v: str) -> str:
        v = v.strip().lower()
        if not re.match(r"^[a-zA-Z0-9._%+\-]{1,64}@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$", v):
            raise ValueError("Enter a valid email address.")
        if len(v) > 254:
            raise ValueError("Email address is too long.")
        blocked = {"mailinator.com", "guerrillamail.com", "tempmail.com"}
        if any(v.endswith("@" + d) for d in blocked):
            raise ValueError("Disposable email addresses are not allowed.")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters.")
        if len(v) > 128:
            raise ValueError("Password is too long (max 128 characters).")
        if not _PWD_UPPER.search(v):
            raise ValueError("Password must contain at least one uppercase letter.")
        if not _PWD_LOWER.search(v):
            raise ValueError("Password must contain at least one lowercase letter.")
        if not _PWD_DIGIT.search(v):
            raise ValueError("Password must contain at least one number.")
        return v

    @field_validator("first_name", "last_name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2:
            raise ValueError("Must be at least 2 characters.")
        if len(v) > 100:
            raise ValueError("Too long (max 100 characters).")
        return v

    @field_validator("phone")
    @classmethod
    def normalise_phone(cls, v: str | None) -> str | None:
        if v is None:
            return None
        clean = re.sub(r"[\s\-()]", "", v)
        if not _PHONE.match(clean):
            raise ValueError("Enter a valid Pakistani mobile number (e.g. 03001234567).")
        if clean.startswith("+92"):   return clean[1:]
        if clean.startswith("0092"):  return clean[2:]
        if clean.startswith("0"):     return "92" + clean[1:]
        return clean


class LoginRequest(DRIPBaseModel):
    email:      str
    password:   str
    totp_code:  str | None = None   # Required for admin accounts

    @field_validator("email")
    @classmethod
    def normalise_email(cls, v: str) -> str:
        return v.strip().lower()


class RefreshRequest(DRIPBaseModel):
    """Refresh token is read from cookie, not body — this schema is unused in routes
    but kept for documentation and testing purposes."""
    pass


class ForgotPasswordRequest(DRIPBaseModel):
    email: str

    @field_validator("email")
    @classmethod
    def normalise_email(cls, v: str) -> str:
        return v.strip().lower()


class ResetPasswordRequest(DRIPBaseModel):
    token:        str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters.")
        if len(v) > 128:
            raise ValueError("Password is too long.")
        if not _PWD_UPPER.search(v):
            raise ValueError("Password must contain at least one uppercase letter.")
        if not _PWD_LOWER.search(v):
            raise ValueError("Password must contain at least one lowercase letter.")
        if not _PWD_DIGIT.search(v):
            raise ValueError("Password must contain at least one number.")
        return v


class ChangePasswordRequest(DRIPBaseModel):
    current_password: str
    new_password:     str

    @field_validator("new_password")
    @classmethod
    def validate_new(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters.")
        if len(v) > 128:
            raise ValueError("Password is too long.")
        if not _PWD_UPPER.search(v):
            raise ValueError("Must contain an uppercase letter.")
        if not _PWD_LOWER.search(v):
            raise ValueError("Must contain a lowercase letter.")
        if not _PWD_DIGIT.search(v):
            raise ValueError("Must contain a number.")
        return v

    @model_validator(mode="after")
    def passwords_differ(self) -> "ChangePasswordRequest":
        if self.current_password == self.new_password:
            raise ValueError("New password must differ from the current password.")
        return self


class VerifyTOTPRequest(DRIPBaseModel):
    code: str

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        v = v.strip()
        if not re.match(r"^\d{6}$", v):
            raise ValueError("TOTP code must be exactly 6 digits.")
        return v


# ── Responses ─────────────────────────────────────────────────────────────────

class UserResponse(DRIPResponseModel):
    id:                 str
    email:              str
    role:               str
    first_name:         str | None
    last_name:          str | None
    phone:              str | None
    avatar_url:         str | None
    has_verified_email: bool
    is_2fa_enabled:     bool
    seller_id:          str | None = None
    created_at:         datetime


class AuthResponse(DRIPResponseModel):
    access_token: str
    token_type:   str = "bearer"
    user:         UserResponse


class TokenResponse(DRIPResponseModel):
    access_token: str
    token_type:   str = "bearer"


class TOTPSetupResponse(DRIPResponseModel):
    secret:  str
    qr_uri:  str
    message: str = "Scan this QR code with your authenticator app, then verify with /auth/setup-2fa/verify"


class MessageResponse(DRIPResponseModel):
    message: str
    success: bool = True