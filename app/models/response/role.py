from pydantic import Field

from app.models.base import CamelCaseModel
from app.models.role import Role


class RoleResponse(CamelCaseModel):
    id: str
    path: str
    description: str
    permissions: list[str] = Field(default_factory=list)
    created_at: str
    deleted_at: str | None = None
    updated_at: str | None = None


class RoleWithInheritanceResponse(RoleResponse):
    inherited_roles: list[RoleResponse] = Field(default_factory=list)

    @classmethod
    def from_role(
        cls, role: Role, inherited_roles: list[Role]
    ) -> "RoleWithInheritanceResponse":
        return cls(
            **role.model_dump(),
            inherited_roles=[
                RoleResponse(**item.model_dump()) for item in inherited_roles
            ],
        )
