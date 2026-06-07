from pydantic import Field

from app.models.base import RequestModel


class CreateRoleRequest(RequestModel):
    id: str
    path: str
    description: str
    permissions: list[str] = Field(default_factory=list)


class ReparentRoleRequest(RequestModel):
    new_parent_id: str


class UpdateRoleRequest(RequestModel):
    path: str | None = None
    description: str | None = None
    permissions: list[str] | None = None
    deleted_at: str | None = None
