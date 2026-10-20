"""Exact PKR response amounts; request pricing policies remain endpoint-specific."""

from decimal import Decimal
from typing import Annotated

from pydantic import Field, PlainSerializer


def _serialize_amount(value: Decimal) -> str:
    """Serialize a response amount as a fixed two-decimal string to preserve PKR precision."""
    return format(value, ".2f")


PKRResponseAmount = Annotated[
    Decimal,
    Field(
        ge=0,
        decimal_places=2,
        allow_inf_nan=False,
        description="PKR major units as a two-decimal string; not integer paisa.",
    ),
    PlainSerializer(_serialize_amount, return_type=str, when_used="json"),
]
