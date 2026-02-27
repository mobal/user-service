import uuid
from contextvars import ContextVar
from datetime import datetime, timedelta
from typing import Any

from aws_lambda_powertools import Logger
from fastapi import status
from fastapi.requests import Request
from fastapi.responses import Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

from app import settings

X_CORRELATION_ID = "X-Correlation-ID"

clients: dict[str, Any] = {}
correlation_id: ContextVar[str] = ContextVar(X_CORRELATION_ID)
logger = Logger(utc=True)


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        correlation_id.set(
            request.headers.get(X_CORRELATION_ID)
            or request.scope.get("aws.context", {}).aws_request_id
            if request.scope.get("aws.context")
            else str(uuid.uuid4())
        )
        logger.set_correlation_id(correlation_id.get())
        response = await call_next(request)
        response.headers[X_CORRELATION_ID] = correlation_id.get()
        return response


class RateLimitingMiddleware(BaseHTTPMiddleware):
    @property
    def _window(self) -> timedelta:
        return timedelta(seconds=settings.rate_limit_duration_in_seconds)

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        if not settings.rate_limiting:
            return await call_next(request)

        client_ip = request.client.host if request.client else None
        if not client_ip:
            return await call_next(request)

        limited = self._check_rate_limit(client_ip)
        if limited is not None:
            return limited

        response = await call_next(request)
        response.headers.update(self._rate_limit_headers(clients[client_ip]))
        return response

    def _check_rate_limit(self, client_ip: str) -> Response | None:
        now = datetime.now()

        client = clients.setdefault(
            client_ip,
            {"request_count": 0, "last_request": now},
        )

        if now - client["last_request"] > self._window:
            client["request_count"] = 1
        else:
            if client["request_count"] >= settings.rate_limit_requests:
                logger.warning("Rate limit exceeded", host=client_ip)
                return Response(
                    content={"message": "Rate limit exceeded. Please try again later"},
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    headers=self._rate_limit_headers(client),
                )
            client["request_count"] += 1

        client["last_request"] = now
        return None

    def _rate_limit_headers(self, client: dict[str, Any]) -> dict[str, str]:
        remaining = max(
            settings.rate_limit_requests - client["request_count"],
            0,
        )

        reset = int((client["last_request"] + self._window).timestamp())

        return {
            "X-RateLimit-Limit": str(settings.rate_limit_requests),
            "X-RateLimit-Remaining": str(remaining),
            "X-RateLimit-Reset": str(reset),
        }
