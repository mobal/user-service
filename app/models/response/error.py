from collections.abc import Sequence

from app.models.base import CamelCaseModel


class ErrorResponse(CamelCaseModel):
    status: int
    error: str
    timestamp: int


class ValidationErrorResponse(ErrorResponse):
    errors: Sequence[dict]
