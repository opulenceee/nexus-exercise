"""Storefront (customer) API — anonymous, no price input.

Customers always pay the minimum_sell_price; there's no way to override it.
This router reuses the shared PurchaseService (channel=DIRECT).
"""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.enums import OrderChannel
from app.repositories.product_repository import ProductRepository
from app.schemas.errors import ErrorResponse
from app.schemas.product import PublicProductOut
from app.schemas.purchase import PurchaseOut
from app.services.product_service import ProductService
from app.services.purchase_service import PurchaseService

router = APIRouter(
    prefix="/api/storefront",
    tags=["storefront"],
)


@router.get("/products", response_model=list[PublicProductOut])
def list_available(db: Session = Depends(get_db)) -> list[PublicProductOut]:
    """All unsold products (price = minimum_sell_price). No auth required."""
    return [PublicProductOut.from_product(p) for p in ProductRepository(db).list_available()]


@router.get(
    "/products/{product_id}",
    response_model=PublicProductOut,
    responses={404: {"model": ErrorResponse}},
)
def get_product(product_id: uuid.UUID, db: Session = Depends(get_db)) -> PublicProductOut:
    return PublicProductOut.from_product(ProductService(db).get(product_id))


@router.post(
    "/products/{product_id}/purchase",
    response_model=PurchaseOut,
    responses={
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
    },
)
def purchase_product(product_id: uuid.UUID, db: Session = Depends(get_db)) -> PurchaseOut:
    """Purchase at the minimum sell price. Customer provides no price — it's set server-side."""
    return PurchaseService(db).purchase(product_id, channel=OrderChannel.DIRECT)
