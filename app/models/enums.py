"""Enumerated types shared across models.

Each inherits from `str` so values serialize cleanly to JSON and compare to
plain strings. Member names == values on purpose, so the Postgres enum labels
and the Python values always match.
"""

import enum


class ProductType(str, enum.Enum):
    # Only COUPON exists today; the schema is built so new types can be added
    # later (a new subtype table + `ALTER TYPE product_type ADD VALUE '...'`).
    COUPON = "COUPON"


class CouponValueType(str, enum.Enum):
    STRING = "STRING"  # value is a code, e.g. "ABCD-1234"
    IMAGE = "IMAGE"    # value is an image URL / data-URI (QR, barcode)


class OrderChannel(str, enum.Enum):
    DIRECT = "DIRECT"      # bought via the storefront at minimum_sell_price
    RESELLER = "RESELLER"  # bought via the reseller API at reseller_price
