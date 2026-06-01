# Nexus Coupon Marketplace

A backend system for a digital marketplace that sells coupon-based products through two channels:

- **Direct customers** — buy via a minimal web frontend at the server-enforced minimum price
- **External resellers** — integrate via a REST API; can mark up above the minimum price

## Quick start

```bash
# 1. Clone and enter the project
git clone https://github.com/opulenceee/nexus-exercise.git
cd nexus-exercise

# 2. Create your local env file (never committed — .env is gitignored)
cp .env.example .env
# Edit .env if you want custom tokens; the defaults work out of the box.

# 3. Build and start everything
docker compose up --build
```

The app starts on **http://localhost:8000** (change `APP_PORT` in `.env` if 8000 is taken).

| URL | What it is |
|---|---|
| `http://localhost:8000/` | Customer storefront |
| `http://localhost:8000/admin` | Admin panel |
| `http://localhost:8000/docs` | Auto-generated Swagger UI (try the API live) |
| `http://localhost:8000/health` | Liveness probe |

> **On first start**, three sample coupons and one demo reseller are seeded automatically (`SEED_ON_START=true`). Tokens are printed in `.env.example`.

---

## Demo credentials (from `.env.example` defaults)

| Role | Token |
|---|---|
| Admin | `dev-admin-token-change-me` |
| Demo reseller | `dev-reseller-token-change-me` |

---

## Running tests

```bash
# All 39 tests (incl. the concurrency test) in Docker:
docker compose run --rm app pytest -v

# Or, if you have Python 3.12+ locally with a venv:
pip install -r requirements-dev.txt
DATABASE_URL=postgresql+psycopg://nexus:local-dev-password@localhost:5432/nexus \
ADMIN_API_TOKEN=dev-admin-token-change-me \
pytest
```

---

## Example `curl` calls

### Reseller API (`/api/v1`)

```bash
TOKEN="dev-reseller-token-change-me"

# List available products
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/products

# Purchase a product (replace <id> with a real UUID from the list)
curl -X POST http://localhost:8000/api/v1/products/<id>/purchase \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"reseller_price": 120.00}'
```

### Admin API (`/api/admin`)

```bash
ADMIN="dev-admin-token-change-me"

# Create a coupon — minimum_sell_price is computed server-side
curl -X POST http://localhost:8000/api/admin/products \
  -H "Authorization: Bearer $ADMIN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Amazon $50 Gift Card",
    "description": "Redeemable on Amazon.com",
    "image_url": "https://example.com/amazon.png",
    "cost_price": "40.00",
    "margin_percentage": "25.00",
    "value_type": "STRING",
    "value": "AMZN-TEST-1234"
  }'
```

---

## Architecture and design decisions

### Tech stack

| Concern | Choice | Why |
|---|---|---|
| Language | **Python 3.12** | Stable, full wheel support. Pinned in Docker for reproducibility regardless of host version. |
| Framework | **FastAPI + Uvicorn** | Pydantic DTOs enforce "never accept pricing fields" structurally; auto-generated Swagger docs let reviewers try the API live. Clean separation into controllers / services / repositories. |
| ORM / migrations | **SQLAlchemy 2.0 (sync) + Alembic** | Sync is easier to reason about; the atomicity guarantee comes from the DB, not the app layer, so async buys no correctness benefit. Real migrations (not `create_all`) mean the schema is reviewable and reversible. |
| Database | **PostgreSQL 16** | `NUMERIC` for money, row-level locking for the atomic sale, strong constraints, enum types. |
| DB driver | **psycopg 3** | Modern, actively maintained. |
| Frontend | **Vanilla HTML/JS via FastAPI StaticFiles** | The brief says "functionality over UI". No build toolchain, no separate container, easiest possible Docker setup. |

### Project structure (layered)

```
app/
  main.py              # mounts routers, exception handlers, static files
  core/
    config.py          # typed env config (pydantic-settings), fail-fast on start
    database.py        # engine, session factory, get_db dependency
    security.py        # token hashing + auth dependencies
    errors.py          # DomainError hierarchy + consistent envelope handlers
  models/              # SQLAlchemy ORM (4 tables)
  schemas/             # Pydantic DTOs, separated by surface
  repositories/        # data access (one class per aggregate; all SQL lives here)
  services/
    pricing.py         # compute_minimum_sell_price (Decimal, ROUND_HALF_UP)
    product_service.py # admin CRUD business rules
    purchase_service.py# the shared atomic purchase (used by both channels)
  api/
    v1/reseller.py     # the FIXED reseller contract
    storefront.py      # customer channel
    admin.py           # admin CRUD
  static/              # index.html, admin.html, styles.css
```

**Why this separation matters:** controllers handle HTTP only (parse input, return output); services contain all business rules; repositories own all SQL. Services are unit-testable with mocked repos; the purchase rule lives in one place and is reused by both channels (DRY).

### Database model (joined-table inheritance)

A `products` table holds the shared base fields; a `coupons` table holds the coupon-specific fields (1:1, FK + CASCADE). Adding a new product type later means adding a new subtype table — the base table and most existing code stay untouched.

```
products               coupons (1:1)
---------              -------------------
id UUID PK             product_id UUID PK/FK → products
name                   cost_price NUMERIC(12,2)  CHECK >= 0
description            margin_percentage         CHECK >= 0
type ENUM(COUPON)      minimum_sell_price        CHECK >= 0  ← derived, never client-set
image_url              is_sold BOOL DEFAULT false
created_at             value_type ENUM(STRING|IMAGE)
updated_at             value TEXT                ← the secret asset

resellers              orders (immutable sale record)
---------              ----------------
id UUID PK             id UUID PK
name                   product_id UUID FK UNIQUE  ← one sale per product
token_hash TEXT UNIQUE channel ENUM(DIRECT|RESELLER)
is_active BOOL         reseller_id UUID FK NULL
created_at             final_price NUMERIC(12,2)
                       created_at
```

Money is `NUMERIC(12,2)`, never `FLOAT`.

### Pricing

```
minimum_sell_price = cost_price × (1 + margin_percentage / 100)
```

Computed **server-side** with Python `Decimal` + `ROUND_HALF_UP` to 2 decimal places. Clients cannot set or override it — neither `minimum_sell_price` nor `is_sold` appear in any input schema.

### The atomic purchase — "sell exactly once"

This is the central correctness guarantee. Both channels (reseller and direct) go through the same `PurchaseService.purchase()` which runs a single transaction:

```
1. SELECT the coupon → 404 if not found
2. if is_sold:      → 409 (fast-fail courtesy check)
3. if reseller && reseller_price < min: → 400 RESELLER_PRICE_TOO_LOW
4. UPDATE coupons SET is_sold = true
   WHERE product_id = :id AND is_sold = false   ← the authoritative atomic claim
   → 0 rows updated = 409 PRODUCT_ALREADY_SOLD (lost the race)
5. INSERT INTO orders (UNIQUE product_id)       ← backstop constraint
6. COMMIT → return { value_type, value, final_price }
```

**Why it's race-proof under concurrency:** PostgreSQL's `UPDATE` statement takes a row lock. If two buyers hit the same coupon simultaneously, one gets the lock and sets `is_sold = true`. The second buyer's `UPDATE` blocks, then re-evaluates the `WHERE is_sold = false` predicate against the now-committed row and updates **0 rows** → 409. No application-level locking, no `SERIALIZABLE` isolation, no retry loop. The `UNIQUE(product_id)` on `orders` is a second database-level safety net.

This exact scenario is covered by `tests/test_purchase_concurrency.py`, which launches 10 concurrent threads and asserts exactly one wins.

### Information hiding

Two secrets have different scopes:

| Secret | Who sees it | Mechanism |
|---|---|---|
| `cost_price`, `margin_percentage` | Admin only | Absent from all public/reseller/customer schemas; `extra="forbid"` on input schemas rejects any attempt to inject them |
| Coupon `value` (the redeemable code) | Buyer, after purchase | Never in list/get responses; only in the `PurchaseOut` schema, returned only after the atomic claim succeeds |

### Auth — why two different approaches

- **Admin**: single internal operator → single `ADMIN_API_TOKEN` env var, compared with `hmac.compare_digest` (constant-time).
- **Resellers**: many external parties, each needing individual identity for the audit trail → tokens stored as SHA-256 hashes in a `resellers` DB table. A high-entropy random token doesn't need a slow KDF like bcrypt (that's for user passwords with limited entropy).

---

## Error envelope

Every error — from validation failures to 500s — returns:

```json
{
  "error_code": "MACHINE_READABLE_CODE",
  "message": "Human readable detail."
}
```

| Code | HTTP | When |
|---|---|---|
| `UNAUTHORIZED` | 401 | Missing/invalid bearer token |
| `VALIDATION_ERROR` | 422 | Malformed request body (e.g. wrong type, extra field) |
| `PRODUCT_NOT_FOUND` | 404 | Product ID doesn't exist |
| `PRODUCT_ALREADY_SOLD` | 409 | Product was already purchased |
| `RESELLER_PRICE_TOO_LOW` | 400 | `reseller_price < minimum_sell_price` |
| `INTERNAL_ERROR` | 500 | Unexpected server error (no stack trace leaked) |

---

## What I'd add in a production system

- **Soft-delete** products instead of hard-delete (preserve the sale history)
- **Pagination** on product listings (`limit` / `offset`)
- **Idempotency keys** on purchase to handle network retries safely
- **Per-reseller rate limiting**
- **Structured logging** (JSON lines) and a metrics endpoint
- **Additional product types** — the joined-table schema makes this a new table + `ALTER TYPE … ADD VALUE`
- **CI pipeline** (GitHub Actions) — run `pytest` on every push

---

## Security notes

- `.env` is gitignored — no secrets committed
- Tokens are never stored in plaintext
- Stack traces are never returned to clients (the `Exception` catch-all returns a generic 500 envelope)
- `minimum_sell_price` and `is_sold` cannot be set by clients (`extra="forbid"` on all input schemas)
