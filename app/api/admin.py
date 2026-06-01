"""Admin API (controllers): REST CRUD over products. Guarded by an admin token.

Controllers stay thin — parse/return DTOs and delegate to the service.
"""

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_admin
from app.schemas.errors import ErrorResponse
from app.schemas.product import AdminProductCreate, AdminProductOut, AdminProductUpdate
from app.services.product_service import ProductService

router = APIRouter(
    prefix="/api/admin",
    tags=["admin"],
    dependencies=[Depends(require_admin)],
    responses={401: {"model": ErrorResponse}},
)


@router.post(
    "/products",
    response_model=AdminProductOut,
    status_code=status.HTTP_201_CREATED,
)
def create_product(payload: AdminProductCreate, db: Session = Depends(get_db)) -> AdminProductOut:
    product = ProductService(db).create(payload)
    return AdminProductOut.from_product(product)


@router.get("/products", response_model=list[AdminProductOut])
def list_products(db: Session = Depends(get_db)) -> list[AdminProductOut]:
    return [AdminProductOut.from_product(p) for p in ProductService(db).list_all()]


@router.get(
    "/products/{product_id}",
    response_model=AdminProductOut,
    responses={404: {"model": ErrorResponse}},
)
def get_product(product_id: uuid.UUID, db: Session = Depends(get_db)) -> AdminProductOut:
    return AdminProductOut.from_product(ProductService(db).get(product_id))


@router.patch(
    "/products/{product_id}",
    response_model=AdminProductOut,
    responses={404: {"model": ErrorResponse}},
)
def update_product(
    product_id: uuid.UUID, payload: AdminProductUpdate, db: Session = Depends(get_db)
) -> AdminProductOut:
    return AdminProductOut.from_product(ProductService(db).update(product_id, payload))


@router.delete(
    "/products/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
)
def delete_product(product_id: uuid.UUID, db: Session = Depends(get_db)) -> None:
    ProductService(db).delete(product_id)
