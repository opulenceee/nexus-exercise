"""FastAPI application: wires routers, exception handlers, and the static frontend."""

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.admin import router as admin_router
from app.api.storefront import router as storefront_router
from app.api.v1.reseller import router as reseller_router
from app.core.config import get_settings
from app.core.errors import register_exception_handlers

settings = get_settings()

app = FastAPI(title=settings.app_name, version="0.1.0")

register_exception_handlers(app)

# --- API routers ---
app.include_router(reseller_router)
app.include_router(storefront_router)
app.include_router(admin_router)

# --- Static frontend ---
# Mount static assets (CSS, JS) at /static.
app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/", include_in_schema=False)
def storefront_page() -> FileResponse:
    """Customer storefront."""
    return FileResponse("app/static/index.html")


@app.get("/admin", include_in_schema=False)
def admin_page() -> FileResponse:
    """Admin panel."""
    return FileResponse("app/static/admin.html")


@app.get("/health", tags=["meta"])
def health() -> dict[str, str]:
    """Liveness probe."""
    return {"status": "ok"}
