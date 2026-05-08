from pydantic import Field

from app.models.base import CamelCaseModel


class CreateRoleRequest(CamelCaseModel):
    id: str
    path: str
    description: str
    permissions: list[str] = Field(default_factory=list)


class ReparentRoleRequest(CamelCaseModel):
    new_parent_id: str


class UpdateRoleRequest(CamelCaseModel):
    path: str | None = None
    description: str | None = None
    permissions: list[str] | None = None
    deleted_at: str | None = None
