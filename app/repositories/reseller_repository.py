"""Data access for resellers (token-hash lookup for authentication)."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.reseller import Reseller


class ResellerRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_active_by_token_hash(self, token_hash: str) -> Reseller | None:
        stmt = select(Reseller).where(
            Reseller.token_hash == token_hash, Reseller.is_active.is_(True)
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def add(self, reseller: Reseller) -> Reseller:
        self.db.add(reseller)
        self.db.flush()
        return reseller
