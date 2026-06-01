"""Reseller API tests — auth, the public shape (no secrets), and purchase rules."""

import uuid


def test_list_requires_auth(client):
    assert client.get("/api/v1/products").status_code == 401


def test_get_requires_auth(client, make_coupon):
    p = make_coupon()
    assert client.get(f"/api/v1/products/{p.id}").status_code == 401


def test_list_returns_public_shape_only(client, reseller_headers, make_coupon):
    make_coupon()
    r = client.get("/api/v1/products", headers=reseller_headers)
    assert r.status_code == 200
    items = r.json()
    assert len(items) == 1
    item = items[0]
    # Exactly the contract fields — no cost/margin/value leak.
    assert set(item.keys()) == {"id", "name", "description", "image_url", "price"}
    assert item["price"] == 100.0  # JSON number == minimum_sell_price


def test_get_by_id_ok_and_hides_value(client, reseller_headers, make_coupon):
    p = make_coupon()
    r = client.get(f"/api/v1/products/{p.id}", headers=reseller_headers)
    assert r.status_code == 200
    assert "value" not in r.json()
    assert "cost_price" not in r.json()


def test_get_unknown_returns_404(client, reseller_headers):
    r = client.get(f"/api/v1/products/{uuid.uuid4()}", headers=reseller_headers)
    assert r.status_code == 404
    assert r.json()["error_code"] == "PRODUCT_NOT_FOUND"


def test_purchase_happy_path_reveals_value(client, reseller_headers, make_coupon):
    p = make_coupon()
    r = client.post(
        f"/api/v1/products/{p.id}/purchase",
        json={"reseller_price": "120.00"},
        headers=reseller_headers,
    )
    assert r.status_code == 200
    body = r.json()
    assert body == {
        "product_id": str(p.id),
        "final_price": 120.0,
        "value_type": "STRING",
        "value": "ABCD-1234",
    }


def test_purchase_at_exactly_min_is_allowed(client, reseller_headers, make_coupon):
    p = make_coupon()  # min == 100.00
    r = client.post(
        f"/api/v1/products/{p.id}/purchase",
        json={"reseller_price": "100.00"},
        headers=reseller_headers,
    )
    assert r.status_code == 200


def test_purchase_below_min_rejected(client, reseller_headers, make_coupon):
    p = make_coupon()
    r = client.post(
        f"/api/v1/products/{p.id}/purchase",
        json={"reseller_price": "99.99"},
        headers=reseller_headers,
    )
    assert r.status_code == 400
    assert r.json()["error_code"] == "RESELLER_PRICE_TOO_LOW"


def test_purchase_missing_price_is_422(client, reseller_headers, make_coupon):
    p = make_coupon()
    r = client.post(f"/api/v1/products/{p.id}/purchase", json={}, headers=reseller_headers)
    assert r.status_code == 422
    assert r.json()["error_code"] == "VALIDATION_ERROR"


def test_purchase_unknown_product_404(client, reseller_headers):
    r = client.post(
        f"/api/v1/products/{uuid.uuid4()}/purchase",
        json={"reseller_price": "120.00"},
        headers=reseller_headers,
    )
    assert r.status_code == 404


def test_purchase_twice_conflicts(client, reseller_headers, make_coupon):
    p = make_coupon()
    first = client.post(
        f"/api/v1/products/{p.id}/purchase",
        json={"reseller_price": "120.00"},
        headers=reseller_headers,
    )
    assert first.status_code == 200
    second = client.post(
        f"/api/v1/products/{p.id}/purchase",
        json={"reseller_price": "120.00"},
        headers=reseller_headers,
    )
    assert second.status_code == 409
    assert second.json()["error_code"] == "PRODUCT_ALREADY_SOLD"


def test_sold_product_excluded_from_list(client, reseller_headers, make_coupon):
    p = make_coupon()
    client.post(
        f"/api/v1/products/{p.id}/purchase",
        json={"reseller_price": "100.00"},
        headers=reseller_headers,
    )
    r = client.get("/api/v1/products", headers=reseller_headers)
    assert all(item["id"] != str(p.id) for item in r.json())
