"""Display-only PKR formatting; never use this to calculate ledger amounts."""

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

type MoneyDisplayValue = Decimal | int | str | float


def format_pkr(value: MoneyDisplayValue) -> str:
    """Render major units with grouping/two places, including legacy queue values.

    Decimal strings avoid binary-float conversion. Historical floats retain only
    their supplied precision; formatting cannot recover already-truncated money.
    """
    try:
        amount = Decimal(str(value))
        if not amount.is_finite():
            raise ValueError("Money must be finite")
        return format(amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP), ",.2f")
    except InvalidOperation as exc:
        raise ValueError("Money must be a valid decimal amount") from exc
