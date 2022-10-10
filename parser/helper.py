"""Parser helpers."""
from decimal import (
    Decimal,
)


def derive_withdrawal(withdrawal: Decimal) -> Decimal:
    """Derive withdrawal values for when deposit is negative."""
    if withdrawal < 0:
        return abs(withdrawal)
    return Decimal(0)


def at_least_0(amount: Decimal) -> Decimal:
    """Make sure this value is at least 0."""
    return max(amount, Decimal(0))
