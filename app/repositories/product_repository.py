"""Data access for the product aggregate (product + its coupon subtype)."""

import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.coupon import Coupon
from app.models.product import Product


class ProductRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(self, product: Product) -> Product:
        """Persist a product (+ cascaded coupon). flush() assigns the PK and
        surfaces any integrity error here rather than at commit time."""
        self.db.add(product)
        self.db.flush()
        return product

    def get(self, product_id: uuid.UUID) -> Product | None:
        """Fetch a product with its coupon eagerly loaded (one query)."""
        stmt = (
            select(Product).options(joinedload(Product.coupon)).where(Product.id == product_id)
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def list_all(self) -> Sequence[Product]:
        """Admin listing — every product, sold or not."""
        stmt = (
            select(Product).options(joinedload(Product.coupon)).order_by(Product.created_at.desc())
        )
        return self.db.execute(stmt).scalars().all()

    def list_available(self) -> Sequence[Product]:
        """Public listing — only products whose coupon is unsold."""
        stmt = (
            select(Product)
            .join(Coupon, Coupon.product_id == Product.id)
            .options(joinedload(Product.coupon))
            .where(Coupon.is_sold.is_(False))
            .order_by(Product.created_at.desc())
        )
        return self.db.execute(stmt).scalars().all()

    def delete(self, product: Product) -> None:
        """Delete a product. If an order references it, the orders FK is
        RESTRICT, so the DB raises IntegrityError (caught by the service)."""
        self.db.delete(product)
        self.db.flush()
