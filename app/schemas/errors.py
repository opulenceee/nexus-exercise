"""The single error envelope used by every error response."""

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    error_code: str  # machine-readable, e.g. "PRODUCT_NOT_FOUND"
    message: str  # human-readable detail
