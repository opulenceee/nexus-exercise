"""Product: the base entity (joined-table inheritance root).

Shared fields live here; type-specific fields live in subtype tables (e.g.
`coupons`). Adding a new product type later means adding a new subtype table —
this base table and most code stay untouched.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum as SAEnum, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import ProductType


class Product(Base):
    __tablename__ = "products"

    # UUIDs are generated app-side (uuid4) — portable, no DB extension needed.
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False)
    type: Mapped[ProductType] = mapped_column(SAEnum(ProductType, name="product_type"), nullable=False)
    image_url: Mapped[str] = mapped_column(String, nullable=False)  # required marketing image
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    # 1:1 to the coupon subtype; deleting a product deletes its coupon row.
    coupon: Mapped["Coupon"] = relationship(  # noqa: F821 (resolved via registry)
        back_populates="product", uselist=False, cascade="all, delete-orphan"
    )
