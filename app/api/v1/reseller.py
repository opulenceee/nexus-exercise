"""Reseller API (controllers) — the FIXED contract under /api/v1.

Every endpoint requires a valid reseller Bearer token. Listings and lookups
return the public shape only (never cost/margin/value); the coupon value is
revealed solely by a successful purchase.
"""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_reseller
from app.models.enums import OrderChannel
from app.models.reseller import Reseller
from app.repositories.product_repository import ProductRepository
from app.schemas.errors import ErrorResponse
from app.schemas.product import PublicProductOut
from app.schemas.purchase import PurchaseOut, ResellerPurchaseIn
from app.services.product_service import ProductService
from app.services.purchase_service import PurchaseService

router = APIRouter(
    prefix="/api/v1",
    tags=["reseller"],
    dependencies=[Depends(get_current_reseller)],
    responses={401: {"model": ErrorResponse}},
)


@router.get("/products", response_model=list[PublicProductOut])
def list_products(db: Session = Depends(get_db)) -> list[PublicProductOut]:
    """All UNSOLD products, public shape, price = minimum_sell_price."""
    products = ProductRepository(db).list_available()
    return [PublicProductOut.from_product(p) for p in products]


@router.get(
    "/products/{product_id}",
    response_model=PublicProductOut,
    responses={404: {"model": ErrorResponse}},
)
def get_product(product_id: uuid.UUID, db: Session = Depends(get_db)) -> PublicProductOut:
    # Returns an existing product whether sold or not (the value is never
    # exposed here); 404 only when it doesn't exist.
    product = ProductService(db).get(product_id)
    return PublicProductOut.from_product(product)


@router.post(
    "/products/{product_id}/purchase",
    response_model=PurchaseOut,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
    },
)
def purchase_product(
    product_id: uuid.UUID,
    payload: ResellerPurchaseIn,
    reseller: Reseller = Depends(get_current_reseller),
    db: Session = Depends(get_db),
) -> PurchaseOut:
    return PurchaseService(db).purchase(
        product_id,
        channel=OrderChannel.RESELLER,
        reseller_price=payload.reseller_price,
        reseller_id=reseller.id,
    )
