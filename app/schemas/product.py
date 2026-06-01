"""Product DTOs, separated by surface.

The separation is the security mechanism: the public/reseller/customer shape
(`PublicProductOut`) simply has no cost/margin/value fields, so those can
neither leak outward nor be injected inward. Admin input models set
`extra="forbid"`, so a client trying to sneak `minimum_sell_price` or
`is_sold` into the body gets a 422.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Annotated

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from app.models.enums import CouponValueType, ProductType

if TYPE_CHECKING:
    from app.models.product import Product

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

    @field_serializer("price")
    def _serialize_price(self, value: Decimal) -> float:
        # The reseller contract shows price as a JSON number (e.g. 100.00).
        return float(value)

    @classmethod
    def from_product(cls, product: Product) -> PublicProductOut:
        # Only the minimum sell price is exposed — never cost/margin/value.
        return cls(
            id=product.id,
            name=product.name,
            description=product.description,
            image_url=product.image_url,
            price=product.coupon.minimum_sell_price,
        )


class AdminProductCreate(BaseModel):
    """Admin create. `minimum_sell_price`/`is_sold` are intentionally absent
    (derived / system-controlled). Unknown fields are rejected."""

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

    @classmethod
    def from_product(cls, product: Product) -> AdminProductOut:
        c = product.coupon
        return cls(
            id=product.id,
            name=product.name,
            description=product.description,
            image_url=product.image_url,
            type=product.type,
            cost_price=c.cost_price,
            margin_percentage=c.margin_percentage,
            minimum_sell_price=c.minimum_sell_price,
            is_sold=c.is_sold,
            value_type=c.value_type,
            value=c.value,
            created_at=product.created_at,
            updated_at=product.updated_at,
        )
