from app.models.base import CamelCaseModel


class CreateRoleRequest(CamelCaseModel):
    role_name: str
    path: str
    permissions: list[str] = []


class ReparentRoleRequest(CamelCaseModel):
    new_parent_name: str


class UpdateRoleRequest(CamelCaseModel):
    role_name: str | None = None
    path: str | None = None
    permissions: list[str] | None = None
    deleted_at: str | None = None
