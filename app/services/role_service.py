from datetime import UTC, datetime
from typing import Any

from aws_lambda_powertools import Logger

from app.exceptions import BadRequestException
from app.models.role import Role
from app.repositories.role_repository import RoleRepository


class RoleService:
    def __init__(
        self,
        role_repository: RoleRepository | None = None,
        logger: Logger | None = None,
    ):
        self._logger = logger or Logger()
        self._role_repository = role_repository or RoleRepository()

    @staticmethod
    def _split_path(path: str) -> list[str]:
        return [segment.strip() for segment in path.split("#")]

    @classmethod
    def _extract_role_name(cls, path: str) -> str:
        return cls._split_path(path)[-1]

    @classmethod
    def _build_lineage_paths(cls, path: str) -> list[str]:
        segments = cls._split_path(path)
        return ["#".join(segments[: index + 1]) for index in range(len(segments))]

    @classmethod
    def _validate_role_path(cls, role_id: str, path: str) -> None:
        segments = cls._split_path(path)
        if not segments or any(not segment for segment in segments):
            raise BadRequestException("Role path must contain non-empty segments")

        if segments[-1] != role_id:
            raise BadRequestException("Role path must end with the role id")

    def create_role(self, data: dict[str, Any]) -> dict[str, Any]:
        self._validate_role_path(data["id"], data["path"])

        role = Role(
            id=data["id"],
            path=data["path"],
            description=data["description"],
            permissions=data.get("permissions", []),
            created_at=datetime.now(UTC).isoformat(),
        )

        self._role_repository.create_role(role.model_dump(exclude_none=True))

        return role.model_dump(exclude_none=True)

    def delete_role(self, role_id: str) -> dict[str, Any]:
        return self._role_repository.delete_role(role_id)

    def update_role(self, role_id: str, data: dict[str, Any]) -> dict[str, Any]:
        if "path" in data:
            self._validate_role_path(role_id, data["path"])

        payload = {**data, "updated_at": datetime.now(UTC).isoformat()}
        return self._role_repository.update_role(role_id, payload)

    def get_role_by_id(self, role_id: str) -> Role | None:
        return self._role_repository.get_by_id(role_id)

    def get_role_by_path(self, path: str) -> Role | None:
        return self._role_repository.get_by_path(path)

    def get_role_by_name(self, role_name: str) -> Role | None:
        return self._role_repository.get_by_name(role_name)

    def get_role_lineage(self, role_id: str) -> list[Role]:
        role = self.get_role_by_id(role_id)
        if not role:
            return []

        lineage: list[Role] = []
        lineage_paths = self._build_lineage_paths(role.path)

        for lineage_path in lineage_paths:
            lineage_role = self._role_repository.get_by_path(lineage_path)
            if lineage_role:
                lineage.append(lineage_role)

        return lineage

    def get_inherited_roles_by_name(
        self, role_name: str
    ) -> tuple[Role, list[Role]] | None:
        role = self.get_role_by_name(role_name)
        if not role:
            return None

        lineage = self.get_role_lineage(role.id)
        inherited_roles = [item for item in lineage if item.id != role.id]
        return role, inherited_roles

    def get_effective_permissions(self, role_ids: list[str]) -> set[str]:
        permissions: set[str] = set()
        for role_id in role_ids:
            for role in self.get_role_lineage(role_id):
                permissions.update(role.permissions)

        return permissions
