"""Product DTOs, separated by surface.

The separation is the security mechanism: the public/reseller/customer shape
(`PublicProductOut`) simply has no cost/margin/value fields, so those can
neither leak outward nor be injected inward. Admin input models set
`extra="forbid"`, so a client trying to sneak `minimum_sell_price` or
`is_sold` into the body gets a 422.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import CouponValueType, ProductType

# Reusable constrained money types (non-negative, 2dp, bounded precision).
CostPrice = Annotated[Decimal, Field(ge=0, max_digits=12, decimal_places=2)]
Margin = Annotated[Decimal, Field(ge=0, max_digits=6, decimal_places=2)]


class PublicProductOut(BaseModel):
    """Returned to resellers AND customers. No cost_price/margin/value."""

    id: uuid.UUID
    name: str
    description: str
    image_url: str
    price: Decimal  # == minimum_sell_price


class AdminProductCreate(BaseModel):
    """Admin create. `minimum_sell_price` and `is_sold` are intentionally absent
    (derived/system-controlled). Unknown fields are rejected."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1)
    image_url: str = Field(min_length=1)
    type: ProductType = ProductType.COUPON
    cost_price: CostPrice
    margin_percentage: Margin
    value_type: CouponValueType
    value: str = Field(min_length=1)


class AdminProductUpdate(BaseModel):
    """Admin partial update (PATCH). Same exclusions as create."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, min_length=1)
    image_url: str | None = Field(default=None, min_length=1)
    cost_price: CostPrice | None = None
    margin_percentage: Margin | None = None
    value_type: CouponValueType | None = None
    value: str | None = Field(default=None, min_length=1)


class AdminProductOut(BaseModel):
    """Admin view — full visibility (admin set these values)."""

    id: uuid.UUID
    name: str
    description: str
    image_url: str
    type: ProductType
    cost_price: Decimal
    margin_percentage: Decimal
    minimum_sell_price: Decimal
    is_sold: bool
    value_type: CouponValueType
    value: str
    created_at: datetime
    updated_at: datetime
