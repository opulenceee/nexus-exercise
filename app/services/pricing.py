"""Server-side pricing.

The minimum sell price is ALWAYS derived here — it is never accepted from a
client. All math uses `Decimal` (never float) with an explicit ROUND_HALF_UP
to 2 decimal places, so monetary rounding is predictable and testable.
"""

from decimal import ROUND_HALF_UP, Decimal

# Quantum for money: 2 decimal places (one implied currency).
_TWO_PLACES = Decimal("0.01")
_HUNDRED = Decimal("100")


def compute_minimum_sell_price(cost_price: Decimal, margin_percentage: Decimal) -> Decimal:
    """Return cost_price * (1 + margin_percentage / 100), rounded to 2dp.

    Examples:
        80.00 @ 25%   -> 100.00
        79.99 @ 25%   ->  99.99   (99.9875 rounds half-up)
        100.00 @ 0%   -> 100.00
    """
    if cost_price < 0:
        raise ValueError("cost_price must be >= 0")
    if margin_percentage < 0:
        raise ValueError("margin_percentage must be >= 0")

    raw = cost_price * (Decimal(1) + (margin_percentage / _HUNDRED))
    return raw.quantize(_TWO_PLACES, rounding=ROUND_HALF_UP)
