"""Parser helpers."""
from decimal import (
    Decimal,
)


def abs_if_negative_else_0(amount: Decimal) -> Decimal:
    """Return the abs of the amount, if it is less than 0, else 0."""
    if amount < 0:
        return abs(amount)
    return Decimal(0)


def at_least_0(amount: Decimal) -> Decimal:
    """Make sure this value is at least 0."""
    return max(amount, Decimal(0))
