"""Data access for orders (immutable sale records)."""

import uuid

from sqlalchemy.orm import Session

from app.models.enums import OrderChannel
from app.models.order import Order


class OrderRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self,
        *,
        product_id: uuid.UUID,
        channel: OrderChannel,
        final_price,
        reseller_id: uuid.UUID | None = None,
    ) -> Order:
        """Insert a sale record. flush() surfaces the UNIQUE(product_id)
        violation immediately if a second sale is somehow attempted."""
        order = Order(
            product_id=product_id,
            channel=channel,
            final_price=final_price,
            reseller_id=reseller_id,
        )
        self.db.add(order)
        self.db.flush()
        return order
