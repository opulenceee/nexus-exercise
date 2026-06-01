"""Order: an immutable record of a single sale.

`UNIQUE(product_id)` is a hard, DB-level guarantee that a product can be sold
at most once — a second layer of safety behind the atomic `is_sold` update.
The product FK is RESTRICT so a sold product can't be silently hard-deleted
(the admin delete handler turns that into a clean 409).
"""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, Numeric, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.enums import OrderChannel


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="RESTRICT"), nullable=False
    )
    channel: Mapped[OrderChannel] = mapped_column(
        SAEnum(OrderChannel, name="order_channel"), nullable=False
    )
    # Null for direct customer sales; set to the calling reseller otherwise.
    reseller_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("resellers.id", ondelete="SET NULL"), nullable=True
    )
    final_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (UniqueConstraint("product_id", name="uq_orders_product_id"),)
