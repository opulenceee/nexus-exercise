"""FastAPI application: wires routers, exception handlers, and (later) the
static frontend.
"""

from fastapi import FastAPI

from app.api.admin import router as admin_router
from app.api.v1.reseller import router as reseller_router
from app.core.config import get_settings
from app.core.errors import register_exception_handlers

settings = get_settings()

app = FastAPI(title=settings.app_name, version="0.1.0")

register_exception_handlers(app)
app.include_router(reseller_router)
app.include_router(admin_router)


@app.get("/health", tags=["meta"])
def health() -> dict[str, str]:
    """Liveness probe."""
    return {"status": "ok"}
