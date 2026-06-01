"""FastAPI application entrypoint.

Routers, exception handlers, and the static frontend are mounted in later
phases. For now this is just enough to prove the container boots and serves
HTTP (with auto-generated Swagger docs at /docs).
"""

from fastapi import FastAPI

from app.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
)


@app.get("/health", tags=["meta"])
def health() -> dict[str, str]:
    """Liveness probe used by humans and (optionally) orchestrators."""
    return {"status": "ok"}
