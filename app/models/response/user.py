from pydantic import Field

from app.models.base import CamelCaseModel


class UserResponse(CamelCaseModel):
    id: str
    display_name: str
    email: str
    username: str
    roles: list[str] = Field(default_factory=list)
    created_at: str
    deleted_at: str | None = None
    last_login_at: str | None = None
    updated_at: str | None = None
