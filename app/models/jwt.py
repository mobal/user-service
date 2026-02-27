from typing import Any

from pydantic import BaseModel


class JWTToken(BaseModel):
    exp: int
    iat: int
    iss: str | None = None
    jti: str
    sub: Any
    user: dict[str, Any]


class RefreshToken(BaseModel):
    token: str
    ttl: int
