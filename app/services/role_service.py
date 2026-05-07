import uuid
from datetime import UTC, datetime
from typing import Any

from aws_lambda_powertools import Logger

from app.models.role import Role
from app.repositories.role_repository import RoleRepository


class RoleService:
    def __init__(self):
        self._logger = Logger()
        self._role_repository = RoleRepository()

    def create_role(self, data: dict[str, Any]) -> dict[str, Any]:
        role = Role(
            id=str(uuid.uuid4()),
            role_name=data["role_name"],
            path=data["path"],
            permissions=data.get("permissions", []),
            created_at=datetime.now(UTC).isoformat(),
        )

        self._role_repository.create_role(role.model_dump(exclude_none=True))

        return role.model_dump(exclude_none=True)

    def delete_role(self, role_id: str) -> dict[str, Any]:
        return self._role_repository.delete_role(role_id)

    def update_role(self, role_id: str, data: dict[str, Any]) -> dict[str, Any]:
        payload = {**data, "updated_at": datetime.now(UTC).isoformat()}
        return self._role_repository.update_role(role_id, payload)

    def get_role_by_id(self, role_id: str) -> Role | None:
        return self._role_repository.get_by_id(role_id)

    def get_role_by_name(self, role_name: str) -> Role | None:
        return self._role_repository.get_by_name(role_name)
