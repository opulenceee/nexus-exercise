"""Domain error hierarchy and the handlers that render the single, consistent
error envelope `{error_code, message}` for every failure.
"""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class DomainError(Exception):
    """Base for business-rule failures. Subclasses set the code + HTTP status."""

    error_code: str = "INTERNAL_ERROR"
    http_status: int = 500

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class ProductNotFound(DomainError):
    error_code = "PRODUCT_NOT_FOUND"
    http_status = 404


class ProductAlreadySold(DomainError):
    error_code = "PRODUCT_ALREADY_SOLD"
    http_status = 409


class ResellerPriceTooLow(DomainError):
    error_code = "RESELLER_PRICE_TOO_LOW"
    http_status = 400


class Unauthorized(DomainError):
    error_code = "UNAUTHORIZED"
    http_status = 401


def _envelope(error_code: str, message: str, status_code: int) -> JSONResponse:
    headers = {"WWW-Authenticate": "Bearer"} if status_code == 401 else None
    return JSONResponse(
        status_code=status_code,
        content={"error_code": error_code, "message": message},
        headers=headers,
    )


def _format_validation(exc: RequestValidationError) -> str:
    parts: list[str] = []
    for err in exc.errors():
        loc = ".".join(str(p) for p in err.get("loc", ()) if p != "body")
        msg = err.get("msg", "invalid")
        parts.append(f"{loc}: {msg}" if loc else msg)
    return "; ".join(parts) or "Invalid request."


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def _handle_domain(_: Request, exc: DomainError) -> JSONResponse:
        return _envelope(exc.error_code, exc.message, exc.http_status)

    @app.exception_handler(RequestValidationError)
    async def _handle_validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        # Body/shape validation (e.g. missing or over-precise reseller_price).
        return _envelope("VALIDATION_ERROR", _format_validation(exc), 422)

    @app.exception_handler(Exception)
    async def _handle_unexpected(_: Request, exc: Exception) -> JSONResponse:
        # Catch-all: never leak stack traces / internals to the client.
        return _envelope("INTERNAL_ERROR", "An unexpected error occurred.", 500)
