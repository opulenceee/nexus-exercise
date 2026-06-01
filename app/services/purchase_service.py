"""The purchase business logic — shared by BOTH selling channels.

This is the heart of the exercise. The "sell exactly once" guarantee comes
from a single atomic conditional UPDATE (see CouponRepository.claim_unsold),
not from application-level locking. The whole operation is one transaction:
claim the row, record the order, commit.
"""

import uuid
from decimal import Decimal

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import ProductAlreadySold, ProductNotFound, ResellerPriceTooLow
from app.models.enums import OrderChannel
from app.repositories.coupon_repository import CouponRepository
from app.repositories.order_repository import OrderRepository
from app.repositories.product_repository import ProductRepository
from app.schemas.purchase import PurchaseOut


class PurchaseService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.products = ProductRepository(db)
        self.coupons = CouponRepository(db)
        self.orders = OrderRepository(db)

    def purchase(
        self,
        product_id: uuid.UUID,
        *,
        channel: OrderChannel,
        reseller_price: Decimal | None = None,
        reseller_id: uuid.UUID | None = None,
    ) -> PurchaseOut:
        product = self.products.get(product_id)
        if product is None or product.coupon is None:
            raise ProductNotFound(f"Product {product_id} not found.")
        coupon = product.coupon

        # Capture what we need before mutating, so it's safe to return post-commit.
        value = coupon.value
        value_type = coupon.value_type
        minimum = coupon.minimum_sell_price

        # Validation order follows the brief: exists -> not sold -> price.
        # (The fast-fail below is a courtesy; the AUTHORITATIVE sold-check is the
        # atomic claim, which is the only thing safe under concurrency.)
        if coupon.is_sold:
            raise ProductAlreadySold(f"Product {product_id} is already sold.")

        if channel is OrderChannel.RESELLER:
            if reseller_price is None:
                raise ResellerPriceTooLow("reseller_price is required.")
            if reseller_price < minimum:
                raise ResellerPriceTooLow("reseller_price is below the minimum sell price.")
            final_price = reseller_price
        else:
            # Direct customer always pays exactly the minimum sell price.
            final_price = minimum

        # Atomic claim: UPDATE ... WHERE is_sold = false. Exactly one concurrent
        # caller updates the row; everyone else gets 0 rows -> already sold.
        if not self.coupons.claim_unsold(product_id):
            raise ProductAlreadySold(f"Product {product_id} is already sold.")

        try:
            self.orders.create(
                product_id=product_id,
                channel=channel,
                final_price=final_price,
                reseller_id=reseller_id,
            )
            self.db.commit()
        except IntegrityError:
            # UNIQUE(product_id) backstop: a sale was already recorded.
            self.db.rollback()
            raise ProductAlreadySold(f"Product {product_id} is already sold.") from None

        return PurchaseOut(
            product_id=product_id,
            final_price=final_price,
            value_type=value_type,
            value=value,
        )
