from datetime import datetime
from typing import Any

import pytest

from app.exceptions import BadRequestException
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
                "id": "SUPER_ADMIN",
                "path": "SUPER_ADMIN",
                "description": "Top level admin role",
                "permissions": ["roles:read", "roles:write"],
            }
        )

        assert result["id"] == "SUPER_ADMIN"
        assert result["path"] == "SUPER_ADMIN"
        assert result["description"] == "Top level admin role"
        assert result["permissions"] == ["roles:read", "roles:write"]
        assert datetime.fromisoformat(result["created_at"])
        create_role_mock.assert_called_once()
        payload = create_role_mock.call_args.args[0]
        assert payload["id"] == result["id"]
        assert payload["description"] == "Top level admin role"

    def test_create_role_defaults_permissions_to_empty_list(
        self, mocker, role_service: RoleService
    ):
        create_role_mock = mocker.patch.object(RoleRepository, "create_role")

        result = role_service.create_role(
            {
                "id": "REGIONAL_VIEWER",
                "path": "SUPER_ADMIN#REGIONAL_VIEWER",
                "description": "Regional viewer",
            }
        )

        assert result["permissions"] == []
        create_role_mock.assert_called_once()

    def test_create_role_rejects_invalid_hierarchy_path(
        self, role_service: RoleService
    ):
        with pytest.raises(BadRequestException, match="Role path must end"):
            role_service.create_role(
                {
                    "id": "STORE_MGR",
                    "path": "SUPER_ADMIN#REGIONAL_MGR",
                    "description": "Invalid store role",
                }
            )

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
            role.id,
            {"path": role.id, "description": "Updated root role"},
        )

        update_role_mock.assert_called_once()
        called_role_id = update_role_mock.call_args.args[0]
        payload = update_role_mock.call_args.args[1]

        assert called_role_id == role.id
        assert payload["path"] == role.id
        assert payload["description"] == "Updated root role"
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

        result = role_service.get_role_by_id("UNKNOWN_ROLE")

        assert result is None

    def test_successfully_get_role_by_name(
        self, mocker, role: Role, role_service: RoleService
    ):
        get_by_name_mock = mocker.patch.object(
            RoleRepository, "get_by_name", return_value=role
        )

        result = role_service.get_role_by_name(role.id)

        assert result == role
        get_by_name_mock.assert_called_once_with(role.id)

    def test_get_role_by_name_returns_none_for_missing_role(
        self, mocker, role_service: RoleService
    ):
        mocker.patch.object(RoleRepository, "get_by_name", return_value=None)

        result = role_service.get_role_by_name("MISSING")

        assert result is None

    def test_get_inherited_roles_by_name_returns_role_and_parents(
        self, mocker, role_service: RoleService
    ):
        store_role = Role(
            id="STORE_MGR",
            path="SUPER_ADMIN#REGIONAL_MGR#STORE_MGR",
            description="Store manager",
            permissions=["stores:write"],
            created_at=datetime.now().isoformat(),
        )
        super_admin_role = Role(
            id="SUPER_ADMIN",
            path="SUPER_ADMIN",
            description="Super admin",
            permissions=["roles:write"],
            created_at=datetime.now().isoformat(),
        )
        regional_role = Role(
            id="REGIONAL_MGR",
            path="SUPER_ADMIN#REGIONAL_MGR",
            description="Regional manager",
            permissions=["regions:write"],
            created_at=datetime.now().isoformat(),
        )

        mocker.patch.object(RoleRepository, "get_by_name", return_value=store_role)
        mocker.patch.object(
            RoleService,
            "get_role_lineage",
            return_value=[super_admin_role, regional_role, store_role],
        )

        result = role_service.get_inherited_roles_by_name("STORE_MGR")

        assert result == (store_role, [super_admin_role, regional_role])

    def test_get_role_lineage_returns_ancestors_in_order(
        self, mocker, role_service: RoleService
    ):
        store_role = Role(
            id="STORE_MGR",
            path="SUPER_ADMIN#REGIONAL_MGR#STORE_MGR",
            description="Store manager",
            permissions=["stores:write"],
            created_at=datetime.now().isoformat(),
        )
        regional_role = Role(
            id="REGIONAL_MGR",
            path="SUPER_ADMIN#REGIONAL_MGR",
            description="Regional manager",
            permissions=["regions:write"],
            created_at=datetime.now().isoformat(),
        )
        super_admin_role = Role(
            id="SUPER_ADMIN",
            path="SUPER_ADMIN",
            description="Super admin",
            permissions=["roles:write"],
            created_at=datetime.now().isoformat(),
        )

        mocker.patch.object(RoleRepository, "get_by_id", return_value=store_role)
        get_by_path_mock = mocker.patch.object(
            RoleRepository,
            "get_by_path",
            side_effect=[super_admin_role, regional_role, store_role],
        )

        result = role_service.get_role_lineage(store_role.id)

        assert result == [super_admin_role, regional_role, store_role]
        assert get_by_path_mock.call_args_list[0].args == ("SUPER_ADMIN",)
        assert get_by_path_mock.call_args_list[1].args == ("SUPER_ADMIN#REGIONAL_MGR",)
        assert get_by_path_mock.call_args_list[2].args == (
            "SUPER_ADMIN#REGIONAL_MGR#STORE_MGR",
        )

    def test_get_role_lineage_with_existing_ancestors(
        self, mocker, role_service: RoleService
    ):
        role_data: dict[str, Any] = {
            "id": "manager_id",
            "path": "root#admin#manager",
            "description": "Manager role",
            "permissions": ["read", "write"],
            "created_at": datetime.now().isoformat(),
        }

        admin_role: dict[str, Any] = {
            "id": "admin_id",
            "path": "root#admin",
            "description": "Admin role",
            "permissions": ["read"],
            "created_at": datetime.now().isoformat(),
        }

        root_role: dict[str, Any] = {
            "id": "root_id",
            "path": "root",
            "description": "Root role",
            "permissions": [],
            "created_at": datetime.now().isoformat(),
        }

        mocker.patch.object(RoleRepository, "get_by_id", return_value=Role(**role_data))
        mocker.patch.object(RoleRepository, "get_by_path").side_effect = lambda path: {
            "root": Role(**root_role),
            "root#admin": Role(**admin_role),
            "root#admin#manager": Role(**role_data),
        }.get(path)

        lineage = role_service.get_role_lineage("manager_id")

        assert len(lineage) == 3
        assert lineage[0].id == "root_id"
        assert lineage[1].id == "admin_id"
        assert lineage[2].id == "manager_id"

    def test_get_role_lineage_with_missing_ancestors(
        self, mocker, role_service: RoleService
    ):
        role_data: dict[str, Any] = {
            "id": "manager_id",
            "path": "root#admin#manager",
            "description": "Manager role",
            "permissions": ["read", "write"],
            "created_at": datetime.now().isoformat(),
        }

        mocker.patch.object(RoleRepository, "get_by_id", return_value=Role(**role_data))
        root_role: dict[str, Any] = {
            "id": "root_id",
            "path": "root",
            "description": "Root role",
            "permissions": [],
            "created_at": datetime.now().isoformat(),
        }
        mocker.patch.object(RoleRepository, "get_by_path").side_effect = lambda path: {
            "root": Role(**root_role),
            "root#admin": None,  # admin role doesn't exist
            "root#admin#manager": Role(**role_data),
        }.get(path)

        lineage = role_service.get_role_lineage("manager_id")

        assert len(lineage) == 2
        assert lineage[0].id == "root_id"
        assert lineage[1].id == "manager_id"
        assert "admin_id" not in [r.id for r in lineage]

    def test_get_role_lineage_empty_role(self, mocker, role_service: RoleService):
        mocker.patch.object(RoleRepository, "get_by_id", return_value=None)

        lineage = role_service.get_role_lineage("nonexistent_id")

        assert lineage == []

    def test_get_effective_permissions_collects_inherited_permissions(
        self, mocker, role_service: RoleService
    ):
        mocker.patch.object(
            RoleService,
            "get_role_lineage",
            return_value=[
                Role(
                    id="SUPER_ADMIN",
                    path="SUPER_ADMIN",
                    description="Super admin",
                    permissions=["roles:write"],
                    created_at=datetime.now().isoformat(),
                ),
                Role(
                    id="STORE_MGR",
                    path="SUPER_ADMIN#STORE_MGR",
                    description="Store manager",
                    permissions=["stores:write"],
                    created_at=datetime.now().isoformat(),
                ),
            ],
        )

        result = role_service.get_effective_permissions(["STORE_MGR"])

        assert result == {"roles:write", "stores:write"}
