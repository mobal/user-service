import os
import uuid
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from fastapi.testclient import TestClient

from app.models.user import User


class TestUserAPI:
    @pytest.fixture
    def test_client(self, initialize_users_table) -> TestClient:
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
            "user": {"roles": ["root"]},
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
            "user": {"roles": ["user"]},
        }
        return jwt.encode(
            payload, os.getenv("JWT_SECRET_SSM_PARAM_VALUE"), algorithm="HS256"
        )

    # GET /v1/healthcheck

    def test_healthcheck_returns_200(self, test_client: TestClient):
        response = test_client.get("/v1/healthcheck")

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    # POST /v1/users

    def test_successfully_register_user(self, test_client: TestClient, root_token: str):
        response = test_client.post(
            "/v1/users",
            json={
                "email": "newuser@squarelabs.hu",
                "username": "newuser",
                "password": "securepassword123",
                "confirmPassword": "securepassword123",
                "displayName": "New User",
            },
            headers={"Authorization": f"Bearer {root_token}"},
        )

        assert response.status_code == 201
        assert "location" in response.headers
        assert response.headers["location"].startswith("/users/")

    def test_register_user_returns_403_without_token(self, test_client: TestClient):
        response = test_client.post(
            "/v1/users",
            json={
                "email": "newuser@squarelabs.hu",
                "username": "newuser",
                "password": "securepassword123",
                "confirmPassword": "securepassword123",
            },
        )

        assert response.status_code == 403

    def test_register_user_returns_403_without_root_role(
        self, test_client: TestClient, user_token: str
    ):
        response = test_client.post(
            "/v1/users",
            json={
                "email": "newuser@squarelabs.hu",
                "username": "newuser",
                "password": "securepassword123",
                "confirmPassword": "securepassword123",
            },
            headers={"Authorization": f"Bearer {user_token}"},
        )

        assert response.status_code == 403

    def test_register_user_returns_422_when_passwords_do_not_match(
        self, test_client: TestClient, root_token: str
    ):
        response = test_client.post(
            "/v1/users",
            json={
                "email": "newuser@squarelabs.hu",
                "username": "newuser",
                "password": "securepassword123",
                "confirmPassword": "differentpassword",
            },
            headers={"Authorization": f"Bearer {root_token}"},
        )

        assert response.status_code == 422

    # DELETE /v1/users/{user_id}

    def test_successfully_delete_user(
        self, test_client: TestClient, root_token: str, user: User
    ):
        response = test_client.delete(
            f"/v1/users/{user.id}",
            headers={"Authorization": f"Bearer {root_token}"},
        )

        assert response.status_code == 204

    def test_delete_user_returns_403_without_token(
        self, test_client: TestClient, user: User
    ):
        response = test_client.delete(f"/v1/users/{user.id}")

        assert response.status_code == 403

    def test_delete_user_returns_403_without_root_role(
        self, test_client: TestClient, user_token: str, user: User
    ):
        response = test_client.delete(
            f"/v1/users/{user.id}",
            headers={"Authorization": f"Bearer {user_token}"},
        )

        assert response.status_code == 403

    # GET /v1/users/{user_id}

    def test_successfully_get_user_by_id(
        self, test_client: TestClient, root_token: str, user: User
    ):
        response = test_client.get(
            f"/v1/users/{user.id}",
            headers={"Authorization": f"Bearer {root_token}"},
        )

        assert response.status_code == 200

    def test_get_user_by_id_returns_403_without_token(
        self, test_client: TestClient, user: User
    ):
        response = test_client.get(f"/v1/users/{user.id}")

        assert response.status_code == 403

    # GET /v1/users

    def test_successfully_get_users(
        self, test_client: TestClient, root_token: str, user: User
    ):
        response = test_client.get(
            "/v1/users",
            headers={"Authorization": f"Bearer {root_token}"},
        )

        assert response.status_code == 200
        body = response.json()
        assert "items" in body

    def test_get_users_returns_403_without_token(self, test_client: TestClient):
        response = test_client.get("/v1/users")

        assert response.status_code == 403

    def test_get_users_returns_403_without_root_role(
        self, test_client: TestClient, user_token: str
    ):
        response = test_client.get(
            "/v1/users",
            headers={"Authorization": f"Bearer {user_token}"},
        )

        assert response.status_code == 403

    def test_successfully_get_users_with_username_filter(
        self, test_client: TestClient, root_token: str, user: User
    ):
        response = test_client.get(
            f"/v1/users?username={user.username}",
            headers={"Authorization": f"Bearer {root_token}"},
        )

        assert response.status_code == 200
        body = response.json()
        assert "items" in body

    # PUT /v1/users/{user_id}

    def test_successfully_update_user(
        self, test_client: TestClient, root_token: str, user: User
    ):
        response = test_client.put(
            f"/v1/users/{user.id}",
            json={"displayName": "Updated Name"},
            headers={"Authorization": f"Bearer {root_token}"},
        )

        assert response.status_code == 204

    def test_update_user_returns_403_without_token(
        self, test_client: TestClient, user: User
    ):
        response = test_client.put(
            f"/v1/users/{user.id}",
            json={"displayName": "Updated Name"},
        )

        assert response.status_code == 403

    def test_update_user_returns_403_without_root_role(
        self, test_client: TestClient, user_token: str, user: User
    ):
        response = test_client.put(
            f"/v1/users/{user.id}",
            json={"displayName": "Updated Name"},
            headers={"Authorization": f"Bearer {user_token}"},
        )

        assert response.status_code == 403
