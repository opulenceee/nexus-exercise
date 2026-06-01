"""The concurrency showpiece: many buyers race for the same coupon; exactly
one wins and exactly one order is recorded.

Threads call the PurchaseService directly, each on its OWN session/connection,
so the race is resolved by real Postgres row-locking — the same mechanism that
protects the live API.
"""

import threading
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

from app.core.errors import ProductAlreadySold
from app.models.enums import OrderChannel
from app.services.purchase_service import PurchaseService

CONCURRENCY = 10


def test_concurrent_purchases_sell_exactly_once(make_coupon, session_factory: sessionmaker):
    product = make_coupon()  # minimum_sell_price = 100.00
    product_id = product.id

    outcomes: list[str] = []
    outcomes_lock = threading.Lock()
    start = threading.Barrier(CONCURRENCY)

    def attempt() -> None:
        start.wait()  # release all threads together to maximize contention
        session = session_factory()
        try:
            PurchaseService(session).purchase(
                product_id,
                channel=OrderChannel.RESELLER,
                reseller_price=Decimal("120.00"),
            )
            result = "won"
        except ProductAlreadySold:
            result = "already_sold"
        finally:
            session.close()
        with outcomes_lock:
            outcomes.append(result)

    threads = [threading.Thread(target=attempt) for _ in range(CONCURRENCY)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert outcomes.count("won") == 1
    assert outcomes.count("already_sold") == CONCURRENCY - 1

    # And the database recorded exactly one sale.
    session = session_factory()
    try:
        count = session.execute(
            text("SELECT count(*) FROM orders WHERE product_id = :pid"),
            {"pid": product_id},
        ).scalar()
    finally:
        session.close()
    assert count == 1
