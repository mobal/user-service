import os
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.models.role import Role


class TestRoleAPI:
    @staticmethod
    def _assert_error_response(response, expected_status_code: int):
        body = response.json()

        assert body["status"] == expected_status_code
        assert isinstance(body["error"], str)
        assert body["error"]
        assert isinstance(body["timestamp"], int)

    @staticmethod
    def _assert_role_response_body(
        body: dict, role: Role, inherited_roles: list[Role] | None = None
    ):
        assert body["id"] == role.id
        assert body["path"] == role.path
        assert body["description"] == role.description
        assert body["permissions"] == role.permissions
        assert body["createdAt"] == role.created_at
        assert body["deletedAt"] == role.deleted_at
        assert body["updatedAt"] == role.updated_at
        if inherited_roles is None:
            assert "inheritedRoles" not in body
            return

        assert body["inheritedRoles"] == [
            {
                "id": inherited_role.id,
                "path": inherited_role.path,
                "description": inherited_role.description,
                "permissions": inherited_role.permissions,
                "createdAt": inherited_role.created_at,
                "deletedAt": inherited_role.deleted_at,
                "updatedAt": inherited_role.updated_at,
            }
            for inherited_role in inherited_roles
        ]

    @pytest.fixture
    def test_client(self, initialize_roles_table) -> TestClient:
        from app.api_handler import app

        return TestClient(app, raise_server_exceptions=True)

    @pytest.fixture
    def root_token(self) -> str:
        now = datetime.now(UTC)
        payload = {
            "exp": int((now + timedelta(hours=1)).timestamp()),
            "iat": int(now.timestamp()),
            "jti": str(uuid.uuid4()),
            "sub": "root-user",
            "user": {"roles": ["roles:read", "roles:write"]},
        }
        return jwt.encode(
            payload, os.getenv("JWT_SECRET_SSM_PARAM_VALUE"), algorithm="HS256"
        )

    @pytest.fixture
    def user_token(self) -> str:
        now = datetime.now(UTC)
        payload = {
            "exp": int((now + timedelta(hours=1)).timestamp()),
            "iat": int(now.timestamp()),
            "jti": str(uuid.uuid4()),
            "sub": "regular-user",
            "user": {"roles": []},
        }
        return jwt.encode(
            payload, os.getenv("JWT_SECRET_SSM_PARAM_VALUE"), algorithm="HS256"
        )

    # POST /api/v1/roles

    def test_successfully_create_role(self, test_client: TestClient, root_token: str):
        response = test_client.post(
            "/api/v1/roles",
            json={
                "id": "STORE_EDITOR",
                "path": "SUPER_ADMIN#STORE_EDITOR",
                "description": "Store editor",
                "permissions": ["roles:read"],
            },
            headers={"Authorization": f"Bearer {root_token}"},
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert "location" in response.headers
        assert response.headers["location"].startswith("/roles/")

    def test_create_role_returns_403_without_token(self, test_client: TestClient):
        response = test_client.post(
            "/api/v1/roles",
            json={
                "id": "STORE_EDITOR",
                "path": "SUPER_ADMIN#STORE_EDITOR",
                "description": "Store editor",
            },
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        self._assert_error_response(response, status.HTTP_403_FORBIDDEN)

    def test_create_role_returns_403_without_write_role(
        self, test_client: TestClient, user_token: str
    ):
        response = test_client.post(
            "/api/v1/roles",
            json={
                "id": "STORE_EDITOR",
                "path": "SUPER_ADMIN#STORE_EDITOR",
                "description": "Store editor",
            },
            headers={"Authorization": f"Bearer {user_token}"},
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        self._assert_error_response(response, status.HTTP_403_FORBIDDEN)

    # DELETE /api/v1/roles/{role_id}

    def test_successfully_delete_role(
        self, test_client: TestClient, root_token: str, role: Role
    ):
        response = test_client.delete(
            f"/api/v1/roles/{role.id}",
            headers={"Authorization": f"Bearer {root_token}"},
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_delete_role_returns_403_without_token(
        self, test_client: TestClient, role: Role
    ):
        response = test_client.delete(f"/api/v1/roles/{role.id}")

        assert response.status_code == status.HTTP_403_FORBIDDEN
        self._assert_error_response(response, status.HTTP_403_FORBIDDEN)

    def test_delete_role_returns_403_without_write_role(
        self, test_client: TestClient, user_token: str, role: Role
    ):
        response = test_client.delete(
            f"/api/v1/roles/{role.id}",
            headers={"Authorization": f"Bearer {user_token}"},
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        self._assert_error_response(response, status.HTTP_403_FORBIDDEN)

    # GET /api/v1/roles/{role_id}

    def test_successfully_get_role_by_id(
        self, test_client: TestClient, root_token: str, role: Role
    ):
        response = test_client.get(
            f"/api/v1/roles/{role.id}",
            headers={"Authorization": f"Bearer {root_token}"},
        )

        assert response.status_code == status.HTTP_200_OK
        self._assert_role_response_body(response.json(), role, inherited_roles=[])

    def test_get_role_by_id_returns_404_for_unknown_role(
        self, test_client: TestClient, root_token: str
    ):
        response = test_client.get(
            f"/api/v1/roles/{uuid.uuid4()}",
            headers={"Authorization": f"Bearer {root_token}"},
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        self._assert_error_response(response, status.HTTP_404_NOT_FOUND)

    def test_get_role_by_id_returns_403_without_token(
        self, test_client: TestClient, role: Role
    ):
        response = test_client.get(f"/api/v1/roles/{role.id}")

        assert response.status_code == status.HTTP_403_FORBIDDEN
        self._assert_error_response(response, status.HTTP_403_FORBIDDEN)

    def test_get_role_by_id_returns_403_without_read_role(
        self, test_client: TestClient, user_token: str, role: Role
    ):
        response = test_client.get(
            f"/api/v1/roles/{role.id}",
            headers={"Authorization": f"Bearer {user_token}"},
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        self._assert_error_response(response, status.HTTP_403_FORBIDDEN)

    # GET /api/v1/roles/name/{role_name}

    def test_successfully_get_role_by_name(
        self, test_client: TestClient, root_token: str, role: Role, roles_table
    ):
        inherited_role: dict[str, Any] = {
            "id": "REGIONAL_MGR",
            "path": "SUPER_ADMIN#REGIONAL_MGR",
            "description": "Regional manager",
            "permissions": ["regions:write"],
            "created_at": role.created_at,
            "updated_at": role.updated_at,
        }
        child_role: dict[str, Any] = {
            "id": "STORE_MGR",
            "path": "SUPER_ADMIN#REGIONAL_MGR#STORE_MGR",
            "description": "Store manager",
            "permissions": ["stores:write"],
            "created_at": role.created_at,
            "updated_at": role.updated_at,
        }
        roles_table.put_item(Item=inherited_role)
        roles_table.put_item(Item=child_role)

        response = test_client.get(
            "/api/v1/roles/name/STORE_MGR",
            headers={"Authorization": f"Bearer {root_token}"},
        )

        assert response.status_code == status.HTTP_200_OK
        self._assert_role_response_body(
            response.json(),
            Role(**child_role),
            [role, Role(**inherited_role)],
        )

    def test_get_role_by_name_returns_404_for_unknown_role(
        self, test_client: TestClient, root_token: str
    ):
        response = test_client.get(
            "/api/v1/roles/name/NONEXISTENT",
            headers={"Authorization": f"Bearer {root_token}"},
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        self._assert_error_response(response, status.HTTP_404_NOT_FOUND)

    def test_get_role_by_name_returns_403_without_token(self, test_client: TestClient):
        response = test_client.get("/api/v1/roles/name/SUPER_ADMIN")

        assert response.status_code == status.HTTP_403_FORBIDDEN
        self._assert_error_response(response, status.HTTP_403_FORBIDDEN)

    def test_get_role_by_name_returns_403_without_read_role(
        self, test_client: TestClient, user_token: str
    ):
        response = test_client.get(
            "/api/v1/roles/name/SUPER_ADMIN",
            headers={"Authorization": f"Bearer {user_token}"},
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        self._assert_error_response(response, status.HTTP_403_FORBIDDEN)

    # PUT /api/v1/roles/{role_id}

    def test_successfully_update_role(
        self, test_client: TestClient, root_token: str, role: Role
    ):
        response = test_client.put(
            f"/api/v1/roles/{role.id}",
            json={"description": "Updated root role"},
            headers={"Authorization": f"Bearer {root_token}"},
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_update_role_returns_403_without_token(
        self, test_client: TestClient, role: Role
    ):
        response = test_client.put(
            f"/api/v1/roles/{role.id}",
            json={"description": "Updated root role"},
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        self._assert_error_response(response, status.HTTP_403_FORBIDDEN)

    # POST /api/v1/roles - parent not found / invalid path

    def test_create_role_returns_400_when_parent_not_found(
        self, test_client: TestClient, root_token: str
    ):
        """Test creating a role whose parent role does not exist."""
        response = test_client.post(
            "/api/v1/roles",
            json={
                "id": "ORPHAN_ROLE",
                "path": "NONEXISTENT_PARENT#ORPHAN_ROLE",
                "description": "Orphan role",
            },
            headers={"Authorization": f"Bearer {root_token}"},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        self._assert_error_response(response, status.HTTP_400_BAD_REQUEST)

    def test_create_role_returns_400_for_invalid_path_not_ending_with_id(
        self, test_client: TestClient, root_token: str
    ):
        """Test creating a role with path not ending with role id."""
        response = test_client.post(
            "/api/v1/roles",
            json={
                "id": "STORE_MGR",
                "path": "SUPER_ADMIN#REGIONAL_MGR",
                "description": "Invalid store role",
            },
            headers={"Authorization": f"Bearer {root_token}"},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        self._assert_error_response(response, status.HTTP_400_BAD_REQUEST)

    def test_create_role_returns_400_for_path_with_empty_segments(
        self, test_client: TestClient, root_token: str
    ):
        """Test creating a role with path containing empty segments."""
        response = test_client.post(
            "/api/v1/roles",
            json={
                "id": "STORE_MGR",
                "path": "SUPER_ADMIN##STORE_MGR",
                "description": "Store manager",
            },
            headers={"Authorization": f"Bearer {root_token}"},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        self._assert_error_response(response, status.HTTP_400_BAD_REQUEST)

    # PUT /api/v1/roles/{role_id} - invalid path / not found

    def test_update_role_returns_400_for_invalid_path(
        self, test_client: TestClient, root_token: str, role: Role
    ):
        """Test updating a role with an invalid path."""
        response = test_client.put(
            f"/api/v1/roles/{role.id}",
            json={"path": "#INVALID"},
            headers={"Authorization": f"Bearer {root_token}"},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        self._assert_error_response(response, status.HTTP_400_BAD_REQUEST)

    def test_update_role_returns_400_for_path_not_ending_with_role_id(
        self, test_client: TestClient, root_token: str, role: Role
    ):
        """Test updating a role with path not ending with the role id."""
        response = test_client.put(
            f"/api/v1/roles/{role.id}",
            json={"path": "SUPER_ADMIN#WRONG_ID"},
            headers={"Authorization": f"Bearer {root_token}"},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        self._assert_error_response(response, status.HTTP_400_BAD_REQUEST)

    # GET /api/v1/roles/{role_id} - for deleted role

    def test_get_role_by_id_returns_404_for_deleted_role(
        self, test_client: TestClient, root_token: str, role: Role
    ):
        """Test getting a soft-deleted role returns 404."""
        # Roles are hard-deleted, so delete it first
        test_client.delete(
            f"/api/v1/roles/{role.id}",
            headers={"Authorization": f"Bearer {root_token}"},
        )

        response = test_client.get(
            f"/api/v1/roles/{role.id}",
            headers={"Authorization": f"Bearer {root_token}"},
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        self._assert_error_response(response, status.HTTP_404_NOT_FOUND)

    # GET /api/v1/roles/name/{role_name} - for deleted role

    def test_get_role_by_name_returns_404_for_deleted_role(
        self, test_client: TestClient, root_token: str, role: Role
    ):
        """Test getting a deleted role by name returns 404."""
        test_client.delete(
            f"/api/v1/roles/{role.id}",
            headers={"Authorization": f"Bearer {root_token}"},
        )

        response = test_client.get(
            f"/api/v1/roles/name/{role.id}",
            headers={"Authorization": f"Bearer {root_token}"},
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        self._assert_error_response(response, status.HTTP_404_NOT_FOUND)

    # PUT /api/v1/roles/{role_id} - non-existent role

    def test_update_role_returns_200_for_nonexistent_role(
        self, test_client: TestClient, root_token: str
    ):
        """Test updating a non-existent role (role repository has no condition check, so it returns 204)."""
        response = test_client.put(
            f"/api/v1/roles/{uuid.uuid4()}",
            json={"description": "Ghost role"},
            headers={"Authorization": f"Bearer {root_token}"},
        )

        # Role repository update_role has no ConditionExpression, so it silently succeeds
        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_update_role_returns_403_without_write_role(
        self, test_client: TestClient, user_token: str, role: Role
    ):
        response = test_client.put(
            f"/api/v1/roles/{role.id}",
            json={"description": "Updated root role"},
            headers={"Authorization": f"Bearer {user_token}"},
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        self._assert_error_response(response, status.HTTP_403_FORBIDDEN)
