import uuid
from datetime import datetime

import pytest

from app.models.role import Role
from app.repositories.role_repository import RoleRepository
from app.services.role_service import RoleService


class TestRoleService:
    @pytest.fixture
    def role_service(self) -> RoleService:
        return RoleService()

    def test_successfully_create_role(self, mocker, role_service: RoleService):
        create_role_mock = mocker.patch.object(RoleRepository, "create_role")

        result = role_service.create_role(
            {
                "role_name": "admin",
                "path": "/admin",
                "permissions": ["roles:read", "roles:write"],
            }
        )

        assert isinstance(uuid.UUID(result["id"]), uuid.UUID)
        assert result["role_name"] == "admin"
        assert result["path"] == "/admin"
        assert result["permissions"] == ["roles:read", "roles:write"]
        assert datetime.fromisoformat(result["created_at"])
        create_role_mock.assert_called_once()
        payload = create_role_mock.call_args.args[0]
        assert payload["id"] == result["id"]
        assert payload["role_name"] == "admin"

    def test_create_role_defaults_permissions_to_empty_list(
        self, mocker, role_service: RoleService
    ):
        create_role_mock = mocker.patch.object(RoleRepository, "create_role")

        result = role_service.create_role({"role_name": "empty", "path": "/empty"})

        assert result["permissions"] == []
        create_role_mock.assert_called_once()

    def test_successfully_delete_role(self, mocker, role_service: RoleService):
        delete_role_mock = mocker.patch.object(RoleRepository, "delete_role")

        role_service.delete_role("some-role-id")

        delete_role_mock.assert_called_once_with("some-role-id")

    def test_successfully_update_role(
        self, mocker, role: Role, role_service: RoleService
    ):
        update_role_mock = mocker.patch.object(
            RoleRepository, "update_role", return_value=role.model_dump()
        )

        role_service.update_role(
            role.id, {"role_name": "updated_admin", "path": "/updated"}
        )

        update_role_mock.assert_called_once()
        called_role_id = update_role_mock.call_args.args[0]
        payload = update_role_mock.call_args.args[1]

        assert called_role_id == role.id
        assert payload["role_name"] == "updated_admin"
        assert payload["path"] == "/updated"
        assert datetime.fromisoformat(payload["updated_at"])

    def test_successfully_get_role_by_id(
        self, mocker, role: Role, role_service: RoleService
    ):
        get_by_id_mock = mocker.patch.object(
            RoleRepository, "get_by_id", return_value=role
        )

        result = role_service.get_role_by_id(role.id)

        assert result == role
        get_by_id_mock.assert_called_once_with(role.id)

    def test_get_role_by_id_returns_none_for_missing_role(
        self, mocker, role_service: RoleService
    ):
        mocker.patch.object(RoleRepository, "get_by_id", return_value=None)

        result = role_service.get_role_by_id(str(uuid.uuid4()))

        assert result is None

    def test_successfully_get_role_by_name(
        self, mocker, role: Role, role_service: RoleService
    ):
        get_by_name_mock = mocker.patch.object(
            RoleRepository, "get_by_name", return_value=role
        )

        result = role_service.get_role_by_name(role.role_name)

        assert result == role
        get_by_name_mock.assert_called_once_with(role.role_name)

    def test_get_role_by_name_returns_none_for_missing_role(
        self, mocker, role_service: RoleService
    ):
        mocker.patch.object(RoleRepository, "get_by_name", return_value=None)

        result = role_service.get_role_by_name("nonexistent-role")

        assert result is None
