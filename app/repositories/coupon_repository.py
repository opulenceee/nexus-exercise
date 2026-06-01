"""Data access for coupons — notably the atomic "claim" used when selling."""

import uuid

from sqlalchemy import update
from sqlalchemy.orm import Session

from app.models.coupon import Coupon


class CouponRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, product_id: uuid.UUID) -> Coupon | None:
        return self.db.get(Coupon, product_id)

    def claim_unsold(self, product_id: uuid.UUID) -> bool:
        """Atomically mark a coupon sold IFF it is currently unsold.

        This is the heart of the concurrency guarantee. A single
        `UPDATE coupons SET is_sold = true WHERE product_id = :id AND is_sold = false`
        takes a row lock; a concurrent second buyer blocks, then re-checks the
        predicate against the just-committed row and updates 0 rows.

        Returns True if THIS call won the sale, False if it was already sold.
        """
        stmt = (
            update(Coupon)
            .where(Coupon.product_id == product_id, Coupon.is_sold.is_(False))
            .values(is_sold=True)
        )
        result = self.db.execute(stmt)
        return result.rowcount == 1
