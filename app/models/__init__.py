"""Importing every model here registers its table on Base.metadata, which is
what Alembic's env.py relies on (it does `import app.models`).
"""

from app.models.coupon import Coupon
from app.models.order import Order
from app.models.product import Product
from app.models.reseller import Reseller

__all__ = ["Product", "Coupon", "Reseller", "Order"]
