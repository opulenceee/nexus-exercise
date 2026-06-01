"""Admin-side product business logic (create / read / update / delete).

The service owns the rule that `minimum_sell_price` is derived (never set by a
client) and recomputed whenever cost or margin changes.
"""

import uuid
from collections.abc import Sequence

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import ProductAlreadySold, ProductNotFound
from app.models.coupon import Coupon
from app.models.product import Product
from app.repositories.product_repository import ProductRepository
from app.schemas.product import AdminProductCreate, AdminProductUpdate
from app.services.pricing import compute_minimum_sell_price


class ProductService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.products = ProductRepository(db)

    def create(self, data: AdminProductCreate) -> Product:
        minimum = compute_minimum_sell_price(data.cost_price, data.margin_percentage)
        product = Product(
            name=data.name,
            description=data.description,
            image_url=data.image_url,
            type=data.type,
            coupon=Coupon(
                cost_price=data.cost_price,
                margin_percentage=data.margin_percentage,
                minimum_sell_price=minimum,
                value_type=data.value_type,
                value=data.value,
            ),
        )
        self.products.add(product)
        self.db.commit()
        self.db.refresh(product)
        return product

    def get(self, product_id: uuid.UUID) -> Product:
        product = self.products.get(product_id)
        if product is None:
            raise ProductNotFound(f"Product {product_id} not found.")
        return product

    def list_all(self) -> Sequence[Product]:
        return self.products.list_all()

    def update(self, product_id: uuid.UUID, data: AdminProductUpdate) -> Product:
        product = self.get(product_id)
        coupon = product.coupon

        if data.name is not None:
            product.name = data.name
        if data.description is not None:
            product.description = data.description
        if data.image_url is not None:
            product.image_url = data.image_url
        if data.value_type is not None:
            coupon.value_type = data.value_type
        if data.value is not None:
            coupon.value = data.value
        if data.cost_price is not None:
            coupon.cost_price = data.cost_price
        if data.margin_percentage is not None:
            coupon.margin_percentage = data.margin_percentage

        # Recompute the derived price if either input changed.
        if data.cost_price is not None or data.margin_percentage is not None:
            coupon.minimum_sell_price = compute_minimum_sell_price(
                coupon.cost_price, coupon.margin_percentage
            )

        self.db.commit()
        self.db.refresh(product)
        return product

    def delete(self, product_id: uuid.UUID) -> None:
        product = self.get(product_id)
        try:
            self.products.delete(product)
            self.db.commit()
        except IntegrityError:
            # An order references this product (FK RESTRICT) — it's been sold.
            self.db.rollback()
            raise ProductAlreadySold(
                "Cannot delete a product that has already been sold."
            ) from None
