from pydantic import EmailStr, Field

from app.models.base import RequestModel


class UserListQueryParams(RequestModel):
    username: str | None = None
    email: EmailStr | None = None
    display_name: str | None = None
    limit: int = Field(default=50, ge=1, le=200)
    next_key: str | None = None
