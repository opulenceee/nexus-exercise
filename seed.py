"""Idempotent seed: create one demo reseller + a few sample coupons.

Run automatically on startup when SEED_ON_START=true. Safe to run multiple
times — skips rows that already exist.

Usage (inside the container):  python -m seed
"""

import sys
from decimal import Decimal

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.security import hash_token
from app.models.coupon import Coupon
from app.models.product import Product
from app.models.reseller import Reseller
from app.models.enums import CouponValueType, ProductType
from app.services.pricing import compute_minimum_sell_price


def seed() -> None:
    settings = get_settings()
    if not settings.seed_reseller_token:
        print("SEED: SEED_RESELLER_TOKEN not set, skipping reseller seed.")
        return

    db = SessionLocal()
    try:
        token_hash = hash_token(settings.seed_reseller_token)

        # --- Reseller ---
        existing = db.query(Reseller).filter_by(token_hash=token_hash).first()
        if existing:
            print("SEED: demo reseller already exists, skipping.")
        else:
            db.add(Reseller(name="Demo Reseller", token_hash=token_hash))
            db.flush()
            print("SEED: created demo reseller.")

        # --- Sample coupons (only if no products exist yet) ---
        if db.query(Product).count() == 0:
            _sample_coupons(db)
            print("SEED: created sample coupons.")
        else:
            print("SEED: products already exist, skipping sample coupons.")

        db.commit()
        print("SEED: done.")
    except Exception as exc:
        db.rollback()
        print(f"SEED ERROR: {exc}", file=sys.stderr)
        raise
    finally:
        db.close()


def _sample_coupons(db) -> None:
    samples = [
        dict(
            name="Amazon $100 Gift Card",
            description="Redeemable on Amazon.com for any purchase.",
            image_url="https://upload.wikimedia.org/wikipedia/commons/a/a9/Amazon_logo.svg",
            cost_price=Decimal("80.00"),
            margin_percentage=Decimal("25.00"),
            value_type=CouponValueType.STRING,
            value="AMZN-XXXX-YYYY-ZZZZ",
        ),
        dict(
            name="Netflix 1-Month Subscription",
            description="One month of Netflix Standard plan.",
            image_url="https://upload.wikimedia.org/wikipedia/commons/0/08/Netflix_2015_logo.svg",
            cost_price=Decimal("12.00"),
            margin_percentage=Decimal("20.00"),
            value_type=CouponValueType.STRING,
            value="NFLX-AAAA-BBBB-CCCC",
        ),
        dict(
            name="Spotify Premium 3 Months",
            description="Three months of Spotify Premium, no ads.",
            image_url="https://upload.wikimedia.org/wikipedia/commons/2/26/Spotify_logo_with_text.svg",
            cost_price=Decimal("25.00"),
            margin_percentage=Decimal("16.00"),
            value_type=CouponValueType.STRING,
            value="SPOT-1111-2222-3333",
        ),
    ]

    for s in samples:
        cost = s.pop("cost_price")
        margin = s.pop("margin_percentage")
        minimum = compute_minimum_sell_price(cost, margin)
        coupon = Coupon(
            cost_price=cost,
            margin_percentage=margin,
            minimum_sell_price=minimum,
            **s,
        )
        product = Product(type=ProductType.COUPON, coupon=coupon, **{
            k: v for k, v in s.items() if k in ("name", "description", "image_url")
        })
        # Reconstruct cleanly: Product takes base fields, Coupon takes the rest.
        product = Product(
            name=s["name"],
            description=s["description"],
            image_url=s["image_url"],
            type=ProductType.COUPON,
            coupon=Coupon(
                cost_price=cost,
                margin_percentage=margin,
                minimum_sell_price=minimum,
                value_type=s["value_type"],
                value=s["value"],
            ),
        )
        db.add(product)
        db.flush()


if __name__ == "__main__":
    seed()
