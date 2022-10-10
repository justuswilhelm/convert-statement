"""Test helper module."""
from decimal import (
    Decimal,
)

from parse import (
    helper,
)


def test_abs_if_negative_else_0() -> None:
    """Test abs_if_negative_else_0."""
    assert helper.abs_if_negative_else_0(Decimal(0)) == Decimal(0)
    assert helper.abs_if_negative_else_0(Decimal(1)) == Decimal(0)
    assert helper.abs_if_negative_else_0(Decimal(-1)) == Decimal(1)
