"""Test fixtures.

Tests run against a dedicated `<db>_test` database in the same Postgres
instance (created on demand). Each test gets a clean slate via TRUNCATE, and
the app's DB dependency is overridden to use the test database.
"""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import Session, sessionmaker

import app.models  # noqa: F401  — registers tables on Base.metadata
from app.core.config import get_settings
from app.core.database import Base, get_db
from app.main import app

_TABLES = ("orders", "coupons", "resellers", "products")


def _url_with_db(database: str) -> str:
    return (
        make_url(get_settings().database_url)
        .set(database=database)
        .render_as_string(hide_password=False)
    )


def _test_db_name() -> str:
    return f"{make_url(get_settings().database_url).database}_test"


@pytest.fixture(scope="session")
def engine() -> Iterator[Engine]:
    test_db = _test_db_name()
    # Create the test database if needed (connect to the maintenance db).
    admin_engine = create_engine(_url_with_db("postgres"), isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as conn:
        exists = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :n"), {"n": test_db}
        ).scalar()
        if not exists:
            conn.execute(text(f'CREATE DATABASE "{test_db}"'))
    admin_engine.dispose()

    eng = create_engine(_url_with_db(test_db), future=True)
    Base.metadata.drop_all(eng)
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture()
def session_factory(engine: Engine):
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@pytest.fixture()
def db_session(session_factory) -> Iterator[Session]:
    session = session_factory()
    session.execute(text("TRUNCATE " + ", ".join(_TABLES) + " RESTART IDENTITY CASCADE"))
    session.commit()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(session_factory, db_session: Session) -> Iterator[TestClient]:
    def override_get_db() -> Iterator[Session]:
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
