"""Authentication helpers and FastAPI dependencies.

- Admin: a single internal operator authenticated against a configured token
  using a constant-time comparison.
- Reseller: many external callers, each with a token whose SHA-256 hash is
  stored in the DB; we hash the incoming token and look the caller up.
"""

import hashlib
import hmac

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.errors import Unauthorized
from app.models.reseller import Reseller
from app.repositories.reseller_repository import ResellerRepository


def hash_token(token: str) -> str:
    """SHA-256 hex digest. Tokens are high-entropy, so a fast hash is correct
    here (unlike user passwords, which need a slow KDF)."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _extract_bearer(request: Request) -> str:
    auth = request.headers.get("Authorization", "")
    scheme, _, token = auth.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise Unauthorized("Missing or malformed bearer token.")
    return token.strip()


def require_admin(request: Request) -> None:
    """Guard admin endpoints. Constant-time compare avoids timing leaks."""
    token = _extract_bearer(request)
    if not hmac.compare_digest(token, get_settings().admin_api_token):
        raise Unauthorized("Invalid admin token.")


def get_current_reseller(request: Request, db: Session = Depends(get_db)) -> Reseller:
    """Resolve and return the authenticated reseller (recorded on the order)."""
    token = _extract_bearer(request)
    reseller = ResellerRepository(db).get_active_by_token_hash(hash_token(token))
    if reseller is None:
        raise Unauthorized("Invalid reseller token.")
    return reseller
