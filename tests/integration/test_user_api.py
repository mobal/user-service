import os
import uuid
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from fastapi import status
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
            "user": {"roles": ["users:read", "users:write"]},
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

    @pytest.fixture
    def expired_root_token(self) -> str:
        now = datetime.now(UTC)
        payload = {
            "exp": int((now - timedelta(minutes=5)).timestamp()),
            "iat": int((now - timedelta(hours=1)).timestamp()),
            "jti": str(uuid.uuid4()),
            "sub": "expired-root-user",
            "user": {"roles": ["root"]},
        }
        return jwt.encode(
            payload, os.getenv("JWT_SECRET_SSM_PARAM_VALUE"), algorithm="HS256"
        )

    @pytest.fixture
    def invalid_signature_token(self) -> str:
        now = datetime.now(UTC)
        payload = {
            "exp": int((now + timedelta(hours=1)).timestamp()),
            "iat": int(now.timestamp()),
            "jti": str(uuid.uuid4()),
            "sub": "root-user-invalid-signature",
            "user": {"roles": ["root"]},
        }
        return jwt.encode(
            payload, "N7f2Qp9Lm4Tx8Vb1Rc6Zd0Hs3Jy5KwEa", algorithm="HS256"
        )

    def test_successfully_register_user(self, test_client: TestClient, root_token: str):
        response = test_client.post(
            "/api/v1/users",
            json={
                "email": "newuser@squarelabs.hu",
                "username": "newuser",
                "password": "securepassword123",
                "confirmPassword": "securepassword123",
                "displayName": "New User",
            },
            headers={"Authorization": f"Bearer {root_token}"},
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert "location" in response.headers
        assert response.headers["location"].startswith("/users/")

    def test_register_user_returns_403_without_token(self, test_client: TestClient):
        response = test_client.post(
            "/api/v1/users",
            json={
                "email": "newuser@squarelabs.hu",
                "username": "newuser",
                "password": "securepassword123",
                "confirmPassword": "securepassword123",
            },
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_register_user_returns_403_without_write_role(
        self, test_client: TestClient, user_token: str
    ):
        response = test_client.post(
            "/api/v1/users",
            json={
                "email": "newuser@squarelabs.hu",
                "username": "newuser",
                "password": "securepassword123",
                "confirmPassword": "securepassword123",
            },
            headers={"Authorization": f"Bearer {user_token}"},
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_register_user_returns_422_when_passwords_do_not_match(
        self, test_client: TestClient, root_token: str
    ):
        response = test_client.post(
            "/api/v1/users",
            json={
                "email": "newuser@squarelabs.hu",
                "username": "newuser",
                "password": "securepassword123",
                "confirmPassword": "differentpassword",
            },
            headers={"Authorization": f"Bearer {root_token}"},
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_register_user_returns_403_for_invalid_signature_token(
        self, test_client: TestClient, invalid_signature_token: str
    ):
        response = test_client.post(
            "/api/v1/users",
            json={
                "email": "newuser@squarelabs.hu",
                "username": "newuser",
                "password": "securepassword123",
                "confirmPassword": "securepassword123",
            },
            headers={"Authorization": f"Bearer {invalid_signature_token}"},
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_register_user_returns_403_for_expired_token(
        self, test_client: TestClient, expired_root_token: str
    ):
        response = test_client.post(
            "/api/v1/users",
            json={
                "email": "newuser@squarelabs.hu",
                "username": "newuser",
                "password": "securepassword123",
                "confirmPassword": "securepassword123",
            },
            headers={"Authorization": f"Bearer {expired_root_token}"},
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_register_user_returns_403_for_malformed_token(
        self, test_client: TestClient
    ):
        response = test_client.post(
            "/api/v1/users",
            json={
                "email": "newuser@squarelabs.hu",
                "username": "newuser",
                "password": "securepassword123",
                "confirmPassword": "securepassword123",
            },
            headers={"Authorization": "Bearer not-a-valid-jwt"},
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_register_user_returns_403_for_invalid_authorization_scheme(
        self, test_client: TestClient, root_token: str
    ):
        response = test_client.post(
            "/api/v1/users",
            json={
                "email": "newuser@squarelabs.hu",
                "username": "newuser",
                "password": "securepassword123",
                "confirmPassword": "securepassword123",
            },
            headers={"Authorization": f"Basic {root_token}"},
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_successfully_delete_user(
        self, test_client: TestClient, root_token: str, user: User
    ):
        response = test_client.delete(
            f"/api/v1/users/{user.id}",
            headers={"Authorization": f"Bearer {root_token}"},
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_delete_user_returns_403_without_token(
        self, test_client: TestClient, user: User
    ):
        response = test_client.delete(f"/api/v1/users/{user.id}")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_delete_user_returns_403_without_write_role(
        self, test_client: TestClient, user_token: str, user: User
    ):
        response = test_client.delete(
            f"/api/v1/users/{user.id}",
            headers={"Authorization": f"Bearer {user_token}"},
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_successfully_get_user_by_id(
        self, test_client: TestClient, root_token: str, user: User
    ):
        response = test_client.get(
            f"/api/v1/users/{user.id}",
            headers={"Authorization": f"Bearer {root_token}"},
        )

        assert response.status_code == status.HTTP_200_OK

    def test_get_user_by_id_returns_403_without_token(
        self, test_client: TestClient, user: User
    ):
        response = test_client.get(f"/api/v1/users/{user.id}")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_successfully_get_user_by_id_with_token_query_param(
        self, test_client: TestClient, root_token: str, user: User
    ):
        response = test_client.get(f"/api/v1/users/{user.id}?token={root_token}")

        assert response.status_code == status.HTTP_200_OK

    def test_get_user_by_id_returns_403_with_invalid_token_query_param(
        self, test_client: TestClient, user: User
    ):
        response = test_client.get(f"/api/v1/users/{user.id}?token=not-a-valid-jwt")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_successfully_get_users(
        self, test_client: TestClient, root_token: str, user: User
    ):
        response = test_client.get(
            "/api/v1/users",
            headers={"Authorization": f"Bearer {root_token}"},
        )

        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert "items" in body

    def test_get_users_returns_403_without_token(self, test_client: TestClient):
        response = test_client.get("/api/v1/users")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_get_users_returns_403_without_read_role(
        self, test_client: TestClient, user_token: str
    ):
        response = test_client.get(
            "/api/v1/users",
            headers={"Authorization": f"Bearer {user_token}"},
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_get_users_returns_400_for_invalid_next_key(
        self, test_client: TestClient, root_token: str
    ):
        response = test_client.get(
            "/api/v1/users?nextKey=asdasdasd",
            headers={"Authorization": f"Bearer {root_token}"},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_successfully_get_users_with_username_filter(
        self, test_client: TestClient, root_token: str, user: User
    ):
        response = test_client.get(
            f"/api/v1/users?username={user.username}",
            headers={"Authorization": f"Bearer {root_token}"},
        )

        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert "items" in body

    def test_successfully_update_user(
        self, test_client: TestClient, root_token: str, user: User
    ):
        response = test_client.put(
            f"/api/v1/users/{user.id}",
            json={"displayName": "Updated Name"},
            headers={"Authorization": f"Bearer {root_token}"},
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_update_user_returns_403_without_token(
        self, test_client: TestClient, user: User
    ):
        response = test_client.put(
            f"/api/v1/users/{user.id}",
            json={"displayName": "Updated Name"},
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_update_user_returns_403_without_write_role(
        self, test_client: TestClient, user_token: str, user: User
    ):
        response = test_client.put(
            f"/api/v1/users/{user.id}",
            json={"displayName": "Updated Name"},
            headers={"Authorization": f"Bearer {user_token}"},
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_successfully_validate_user(
        self, test_client: TestClient, root_token: str, user: User, password: str
    ):
        response = test_client.post(
            f"/api/v1/users/{user.id}/validate",
            json={"password": password},
            headers={"Authorization": f"Bearer {root_token}"},
        )

        assert response.status_code == status.HTTP_200_OK

    def test_validate_user_returns_403_without_token(
        self, test_client: TestClient, user: User
    ):
        response = test_client.post(
            f"/api/v1/users/{user.id}/validate",
            json={"password": "some_password"},
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_validate_user_returns_403_without_read_role(
        self, test_client: TestClient, user_token: str, user: User
    ):
        response = test_client.post(
            f"/api/v1/users/{user.id}/validate",
            json={"password": "some_password"},
            headers={"Authorization": f"Bearer {user_token}"},
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_validate_user_returns_404_for_unknown_user_id(
        self, test_client: TestClient, root_token: str
    ):
        response = test_client.post(
            f"/api/v1/users/{uuid.uuid4()}/validate",
            json={"password": "some_password"},
            headers={"Authorization": f"Bearer {root_token}"},
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_validate_user_returns_400_for_invalid_password(
        self, test_client: TestClient, root_token: str, user: User
    ):
        response = test_client.post(
            f"/api/v1/users/{user.id}/validate",
            json={"password": "wrong_password"},
            headers={"Authorization": f"Bearer {root_token}"},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
