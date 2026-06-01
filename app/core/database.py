"""Database engine, session factory, and the FastAPI DB dependency.

Sync SQLAlchemy 2.0 is intentional: the marketplace's correctness guarantee
(selling a coupon exactly once) is enforced by the *database* via row locks,
not by application-level concurrency, so async would add complexity for no
correctness benefit.
"""

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings

engine = create_engine(
    get_settings().database_url,
    pool_pre_ping=True,  # transparently recycle dropped connections
    future=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    # Keep attributes readable after commit() — needed so we can return the
    # coupon value right after the purchase transaction commits.
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Declarative base shared by all ORM models."""


def get_db() -> Iterator[Session]:
    """Yield a request-scoped session and always close it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
