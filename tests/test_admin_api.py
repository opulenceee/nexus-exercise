"""Admin API tests: auth, derived pricing, input protection, CRUD, delete rules."""

import uuid
from decimal import Decimal

from app.core.config import get_settings
from app.models.enums import OrderChannel
from app.models.order import Order

ADMIN = {"Authorization": f"Bearer {get_settings().admin_api_token}"}


def _payload(**overrides) -> dict:
    base = {
        "name": "Amazon $100 Coupon",
        "description": "Gift card",
        "image_url": "https://example.com/img.png",
        "cost_price": "80.00",
        "margin_percentage": "25.00",
        "value_type": "STRING",
        "value": "ABCD-1234",
    }
    base.update(overrides)
    return base


def _dec(value) -> Decimal:
    # Robust to Decimal being serialized as a JSON number or string.
    return Decimal(str(value))


def test_create_requires_admin_token(client):
    r = client.post("/api/admin/products", json=_payload())
    assert r.status_code == 401
    assert r.json()["error_code"] == "UNAUTHORIZED"


def test_create_computes_minimum_sell_price(client):
    r = client.post("/api/admin/products", json=_payload(), headers=ADMIN)
    assert r.status_code == 201
    body = r.json()
    assert _dec(body["minimum_sell_price"]) == Decimal("100.00")  # 80 * 1.25
    assert body["is_sold"] is False


def test_create_rejects_unknown_field(client):
    # Attempt to inject a server-controlled field -> 422 (extra="forbid").
    r = client.post("/api/admin/products", json=_payload(minimum_sell_price="1.00"), headers=ADMIN)
    assert r.status_code == 422
    assert r.json()["error_code"] == "VALIDATION_ERROR"


def test_create_rejects_is_sold_injection(client):
    r = client.post("/api/admin/products", json=_payload(is_sold=False), headers=ADMIN)
    assert r.status_code == 422


def test_create_rejects_negative_cost(client):
    r = client.post("/api/admin/products", json=_payload(cost_price="-1.00"), headers=ADMIN)
    assert r.status_code == 422


def test_list_returns_all(client):
    client.post("/api/admin/products", json=_payload(), headers=ADMIN)
    client.post("/api/admin/products", json=_payload(name="Second"), headers=ADMIN)
    r = client.get("/api/admin/products", headers=ADMIN)
    assert r.status_code == 200
    assert len(r.json()) == 2


def test_update_recomputes_minimum(client):
    pid = client.post("/api/admin/products", json=_payload(), headers=ADMIN).json()["id"]
    r = client.patch(f"/api/admin/products/{pid}", json={"cost_price": "100.00"}, headers=ADMIN)
    assert r.status_code == 200
    assert _dec(r.json()["minimum_sell_price"]) == Decimal("125.00")  # 100 * 1.25


def test_get_unknown_returns_404(client):
    r = client.get(f"/api/admin/products/{uuid.uuid4()}", headers=ADMIN)
    assert r.status_code == 404
    assert r.json()["error_code"] == "PRODUCT_NOT_FOUND"


def test_delete_unsold_ok(client):
    pid = client.post("/api/admin/products", json=_payload(), headers=ADMIN).json()["id"]
    assert client.delete(f"/api/admin/products/{pid}", headers=ADMIN).status_code == 204
    assert client.get(f"/api/admin/products/{pid}", headers=ADMIN).status_code == 404


def test_delete_sold_is_blocked(client, db_session):
    pid = client.post("/api/admin/products", json=_payload(), headers=ADMIN).json()["id"]
    # Simulate a completed sale: an order referencing the product.
    db_session.add(
        Order(product_id=uuid.UUID(pid), channel=OrderChannel.DIRECT, final_price=Decimal("100.00"))
    )
    db_session.commit()
    r = client.delete(f"/api/admin/products/{pid}", headers=ADMIN)
    assert r.status_code == 409
    assert r.json()["error_code"] == "PRODUCT_ALREADY_SOLD"
