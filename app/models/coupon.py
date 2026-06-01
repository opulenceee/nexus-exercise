"""Coupon: the COUPON product subtype (1:1 with products).

Holds pricing + the redeemable asset. `minimum_sell_price` is DERIVED and
written only by the server (the pricing service); it is never accepted from a
client. CHECK constraints enforce the non-negativity rules at the DB level —
defense in depth alongside the Pydantic validators.
"""

import uuid
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Numeric,
    String,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import CouponValueType


class Coupon(Base):
    __tablename__ = "coupons"

    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        primary_key=True,
    )
    cost_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    margin_percentage: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    minimum_sell_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    is_sold: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    value_type: Mapped[CouponValueType] = mapped_column(
        SAEnum(CouponValueType, name="coupon_value_type"), nullable=False
    )
    # The secret redeemable asset — only ever returned after a successful purchase.
    value: Mapped[str] = mapped_column(String, nullable=False)

    product: Mapped["Product"] = relationship(back_populates="coupon")  # noqa: F821

    __table_args__ = (
        CheckConstraint("cost_price >= 0", name="ck_coupons_cost_price_nonneg"),
        CheckConstraint("margin_percentage >= 0", name="ck_coupons_margin_nonneg"),
        CheckConstraint("minimum_sell_price >= 0", name="ck_coupons_min_sell_nonneg"),
        # Partial index: most lookups filter to unsold coupons.
        Index("ix_coupons_unsold", "is_sold", postgresql_where=text("is_sold = false")),
    )
