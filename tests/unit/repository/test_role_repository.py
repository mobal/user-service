import uuid
from datetime import UTC, datetime

import pytest

from app.models.role import Role
from app.repositories.role_repository import RoleRepository


class TestRoleRepository:
    @pytest.fixture
    def role_repository(self) -> RoleRepository:
        return RoleRepository()

    def test_successfully_create_role(
        self, role_repository: RoleRepository, roles_table
    ):
        new_role_id = "STORE_AUDITOR"
        role_data = {
            "id": new_role_id,
            "path": "SUPER_ADMIN#STORE_AUDITOR",
            "description": "Store auditor",
            "permissions": ["audit:read"],
            "created_at": datetime.now(UTC).isoformat(),
        }

        role_repository.create_role(role_data)

        response = roles_table.get_item(Key={"id": new_role_id})

        assert response["Item"] == role_data

    def test_successfully_delete_role(
        self, role: Role, role_repository: RoleRepository, roles_table
    ):
        role_repository.delete_role(role.id)

        response = roles_table.get_item(Key={"id": role.id})

        assert "Item" not in response

    def test_delete_role_returns_success_for_missing_id(
        self, role_repository: RoleRepository, roles_table
    ):
        response = role_repository.delete_role(str(uuid.uuid4()))

        assert response["ResponseMetadata"]["HTTPStatusCode"] == 200

    def test_successfully_update_role(
        self, role: Role, role_repository: RoleRepository, roles_table
    ):
        updated_at = datetime.now(UTC).isoformat()

        response = role_repository.update_role(
            role.id,
            {
                "id": str(uuid.uuid4()),
                "path": "SUPER_ADMIN",
                "description": "Updated root role",
                "permissions": ["roles:read", "roles:write", "users:write"],
                "updated_at": updated_at,
            },
        )

        item = roles_table.get_item(Key={"id": role.id})["Item"]

        assert response["id"] == role.id
        assert item["id"] == role.id
        assert response["path"] == "SUPER_ADMIN"
        assert item["path"] == "SUPER_ADMIN"
        assert response["description"] == "Updated root role"
        assert item["description"] == "Updated root role"
        assert response["permissions"] == [
            "roles:read",
            "roles:write",
            "users:write",
        ]
        assert item["permissions"] == [
            "roles:read",
            "roles:write",
            "users:write",
        ]
        assert response["updated_at"] == updated_at
        assert item["updated_at"] == updated_at

    def test_update_role_returns_empty_dict_when_only_id_is_provided(
        self, role: Role, role_repository: RoleRepository
    ):
        response = role_repository.update_role(role.id, {"id": role.id})

        assert response == {}

    def test_successfully_get_role_by_id(
        self, role: Role, role_repository: RoleRepository, roles_table
    ):
        item = role_repository.get_by_id(role.id)

        assert item == role

    def test_get_by_id_returns_none_for_missing_role(
        self, role_repository: RoleRepository, roles_table
    ):
        item = role_repository.get_by_id(str(uuid.uuid4()))

        assert item is None

    def test_get_by_id_returns_none_for_soft_deleted_role(
        self, role: Role, role_repository: RoleRepository, roles_table
    ):
        deleted_at = datetime.now(UTC).isoformat()
        roles_table.update_item(
            Key={"id": role.id},
            UpdateExpression="SET deleted_at = :deleted_at",
            ExpressionAttributeValues={":deleted_at": deleted_at},
        )

        item = role_repository.get_by_id(role.id)

        assert item is None

    def test_successfully_get_role_by_path(
        self, role: Role, role_repository: RoleRepository, roles_table
    ):
        item = role_repository.get_by_path(role.path)

        assert item == role

    def test_successfully_get_role_by_name(
        self, role: Role, role_repository: RoleRepository, roles_table
    ):
        item = role_repository.get_by_name(role.id)

        assert item == role

    def test_get_by_path_returns_none_for_missing_role(
        self, role_repository: RoleRepository, roles_table
    ):
        item = role_repository.get_by_path("SUPER_ADMIN#NONEXISTENT")

        assert item is None

    def test_get_by_name_returns_none_for_missing_role(
        self, role_repository: RoleRepository, roles_table
    ):
        item = role_repository.get_by_name("NONEXISTENT")

        assert item is None

    def test_get_by_path_returns_none_for_soft_deleted_role(
        self, role: Role, role_repository: RoleRepository, roles_table
    ):
        deleted_at = datetime.now(UTC).isoformat()
        roles_table.update_item(
            Key={"id": role.id},
            UpdateExpression="SET deleted_at = :deleted_at",
            ExpressionAttributeValues={":deleted_at": deleted_at},
        )

        item = role_repository.get_by_path(role.path)

        assert item is None

    def test_get_by_name_returns_none_for_soft_deleted_role(
        self, role: Role, role_repository: RoleRepository, roles_table
    ):
        deleted_at = datetime.now(UTC).isoformat()
        roles_table.update_item(
            Key={"id": role.id},
            UpdateExpression="SET deleted_at = :deleted_at",
            ExpressionAttributeValues={":deleted_at": deleted_at},
        )

        item = role_repository.get_by_name(role.id)

        assert item is None
