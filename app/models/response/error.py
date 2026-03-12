import time
from collections.abc import Sequence

from app.models.models import CamelModel


class ErrorResponse(CamelModel):
    status: int
    error: str
    timestamp: int = int(time.time())


class ValidationErrorResponse(ErrorResponse):
    errors: Sequence[dict]
