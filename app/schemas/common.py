"""
app/schemas/common.py
─────────────────────
Shared Pydantic v2 schemas used by multiple API modules.

  • Request/response base classes
  • Pagination schemas (cursor + page-based)
  • Standard error response
  • Common field types with validators
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime
from typing import Annotated, Any, Generic, TypeVar

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

T = TypeVar("T")


# ── Base model configuration ──────────────────────────────────────────────────

class DRIPBaseModel(BaseModel):
    """Base for all DRIP schemas. Forbids extra fields by default."""
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
        use_enum_values=True,
        json_encoders={
            datetime: lambda v: v.isoformat(),
            uuid.UUID: str,
        },
    )


class DRIPResponseModel(BaseModel):
    """Base for response schemas. Allows extra for forward compatibility."""
    model_config = ConfigDict(
        extra="ignore",
        from_attributes=True,       # ORM mode
        populate_by_name=True,
        json_encoders={
            datetime: lambda v: v.isoformat(),
            uuid.UUID: str,
        },
    )


# ── Pagination ────────────────────────────────────────────────────────────────

class CursorPagination(DRIPResponseModel):
    """Cursor-based pagination metadata (for catalogue endpoints)."""
    next_cursor: str | None = None
    has_next:    bool = False
    limit:       int


class PagePagination(DRIPResponseModel):
    """Page-based pagination metadata (for admin list endpoints)."""
    page:        int
    per_page:    int
    total:       int
    total_pages: int

    @property
    def has_next(self) -> bool:
        return self.page < self.total_pages

    @property
    def has_prev(self) -> bool:
        return self.page > 1


class PaginatedResponse(DRIPResponseModel, Generic[T]):
    """Generic paginated response wrapper."""
    data:       list[T]
    pagination: PagePagination | CursorPagination


# ── Error response ────────────────────────────────────────────────────────────

class ErrorDetail(DRIPResponseModel):
    code:       str
    message:    str
    fields:     dict[str, str] | None = None
    request_id: str | None = None


class ErrorResponse(DRIPResponseModel):
    error: ErrorDetail


class MessageResponse(DRIPResponseModel):
    """Simple success message response."""
    message: str
    success: bool = True


# ── Common field types ────────────────────────────────────────────────────────

# Pakistani mobile number pattern
_PHONE_PATTERN = re.compile(r"^(\+92|0092|0)?3[0-9]{9}$")

PhoneStr  = Annotated[str, Field(min_length=10, max_length=20)]
EmailStr  = Annotated[str, Field(max_length=254)]
SlugStr   = Annotated[str, Field(min_length=2, max_length=120, pattern=r"^[a-z0-9\-]+$")]
NameStr   = Annotated[str, Field(min_length=2, max_length=200)]
BrandStr  = Annotated[str, Field(min_length=2, max_length=100)]
DescText  = Annotated[str, Field(min_length=10, max_length=5000)]
ShortText = Annotated[str, Field(max_length=500)]


def validate_phone(v: str) -> str:
    """Normalise a Pakistani phone number to international format 923XXXXXXXXX."""
    clean = re.sub(r"[\s\-()]", "", v)
    if not _PHONE_PATTERN.match(clean):
        raise ValueError(
            "Enter a valid Pakistani mobile number. "
            "Formats accepted: 03001234567, +923001234567"
        )
    # Normalise
    if clean.startswith("+92"):
        return clean[1:]
    if clean.startswith("0092"):
        return clean[2:]
    if clean.startswith("0"):
        return "92" + clean[1:]
    return clean


# ── PKR money type ────────────────────────────────────────────────────────────

class PKRAmount(int):
    """
    Monetary amount in PKR (Pakistani Rupees).
    Stored and transmitted as integer PKR — no paisa subdivision.
    """

    @classmethod
    def __get_validators__(cls):  # Pydantic v1 compat
        yield cls.validate

    @classmethod
    def validate(cls, v: Any) -> "PKRAmount":
        if not isinstance(v, int | float):
            raise ValueError("Amount must be a number")
        amount = int(v)
        if amount < 0:
            raise ValueError("Amount cannot be negative")
        if amount > 10_000_000:
            raise ValueError("Amount exceeds maximum allowed value")
        return cls(amount)


# ── Query parameter schemas ───────────────────────────────────────────────────

class PaginationParams(DRIPBaseModel):
    """Standard query params for page-based endpoints."""
    page:     int = Field(default=1, ge=1, le=10000)
    per_page: int = Field(default=25, ge=1, le=100)

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.per_page


class DateRangeParams(DRIPBaseModel):
    """Optional date range filter."""
    date_from: datetime | None = None
    date_to:   datetime | None = None

    @model_validator(mode="after")
    def validate_range(self) -> "DateRangeParams":
        if self.date_from and self.date_to:
            if self.date_from > self.date_to:
                raise ValueError("date_from must be before date_to")
        return self


# ── Health check ─────────────────────────────────────────────────────────────

class HealthResponse(DRIPResponseModel):
    status:      str
    database:    str
    redis:       str
    version:     str
    environment: str