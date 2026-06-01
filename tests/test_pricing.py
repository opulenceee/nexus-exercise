"""Unit tests for the pricing formula — the rounding behavior is a likely
interview talking point, so it's pinned explicitly."""

from decimal import Decimal

import pytest

from app.services.pricing import compute_minimum_sell_price


@pytest.mark.parametrize(
    ("cost", "margin", "expected"),
    [
        ("80", "25", "100.00"),     # the brief's worked example
        ("79.99", "25", "99.99"),   # 99.9875 -> rounds half-up
        ("100", "0", "100.00"),     # zero margin
        ("0", "50", "0.00"),        # zero cost
        ("10", "33.33", "13.33"),   # 13.333 -> rounds down
        ("19.99", "10", "21.99"),   # 21.989 -> rounds up
    ],
)
def test_compute_minimum_sell_price(cost: str, margin: str, expected: str) -> None:
    assert compute_minimum_sell_price(Decimal(cost), Decimal(margin)) == Decimal(expected)


def test_rounds_half_up_not_half_even() -> None:
    # 1.00 * 1.005 = 1.005 -> HALF_UP gives 1.01 (banker's rounding would give 1.00).
    assert compute_minimum_sell_price(Decimal("1.00"), Decimal("0.5")) == Decimal("1.01")


@pytest.mark.parametrize(("cost", "margin"), [("-1", "10"), ("10", "-5")])
def test_negative_inputs_rejected(cost: str, margin: str) -> None:
    with pytest.raises(ValueError):
        compute_minimum_sell_price(Decimal(cost), Decimal(margin))
