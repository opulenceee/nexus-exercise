"""Purchase DTOs.

`reseller_price` is validated here only for *shape* (a positive, 2dp money
value) — a missing/negative/over-precise value is a 422 VALIDATION_ERROR.
The business rule `reseller_price >= minimum_sell_price` lives in the service
and yields the distinct RESELLER_PRICE_TOO_LOW error.
"""

import uuid
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import CouponValueType

ResellerPrice = Annotated[Decimal, Field(gt=0, max_digits=12, decimal_places=2)]


class ResellerPurchaseIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reseller_price: ResellerPrice


class PurchaseOut(BaseModel):
    """Returned only after a successful purchase — this is the one place the
    coupon `value` is ever exposed."""

    product_id: uuid.UUID
    final_price: Decimal
    value_type: CouponValueType
    value: str
