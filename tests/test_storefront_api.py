"""Storefront (customer channel) tests."""

import uuid


def test_list_available_no_auth(client, make_coupon):
    make_coupon()
    r = client.get("/api/storefront/products")
    assert r.status_code == 200
    items = r.json()
    assert len(items) == 1
    assert set(items[0].keys()) == {"id", "name", "description", "image_url", "price"}


def test_list_excludes_sold(client, reseller_headers, make_coupon):
    p = make_coupon()
    # Sell it via the reseller channel.
    client.post(
        f"/api/v1/products/{p.id}/purchase",
        json={"reseller_price": "100.00"},
        headers=reseller_headers,
    )
    r = client.get("/api/storefront/products")
    assert r.status_code == 200
    assert r.json() == []


def test_get_product_not_found(client):
    r = client.get(f"/api/storefront/products/{uuid.uuid4()}")
    assert r.status_code == 404
    assert r.json()["error_code"] == "PRODUCT_NOT_FOUND"


def test_purchase_at_minimum_price(client, make_coupon):
    p = make_coupon()  # min sell price = 100.00
    r = client.post(f"/api/storefront/products/{p.id}/purchase")
    assert r.status_code == 200
    body = r.json()
    assert body["final_price"] == 100.0
    assert body["value"] == "ABCD-1234"
    assert body["product_id"] == str(p.id)


def test_purchase_reveals_value(client, make_coupon):
    p = make_coupon(value="SECRET-CODE-XYZ")
    r = client.post(f"/api/storefront/products/{p.id}/purchase")
    assert r.status_code == 200
    assert r.json()["value"] == "SECRET-CODE-XYZ"


def test_double_purchase_409(client, make_coupon):
    p = make_coupon()
    client.post(f"/api/storefront/products/{p.id}/purchase")
    r = client.post(f"/api/storefront/products/{p.id}/purchase")
    assert r.status_code == 409
    assert r.json()["error_code"] == "PRODUCT_ALREADY_SOLD"


def test_purchase_not_found(client):
    r = client.post(f"/api/storefront/products/{uuid.uuid4()}/purchase")
    assert r.status_code == 404
