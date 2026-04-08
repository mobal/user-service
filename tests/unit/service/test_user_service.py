import json
import uuid
from base64 import urlsafe_b64encode
from datetime import datetime

import pytest
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.exceptions import (
    InvalidPaginationKeyException,
    InvalidPasswordException,
    UserNotFoundException,
)
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.services.user_service import UserService


class TestUserService:
    @pytest.fixture
    def user_service(self) -> UserService:
        return UserService()

    def test_filter_users_successfully_returns_users(
        self, mocker, user: User, user_service: UserService
    ):
        mocker.patch.object(UserRepository, "filter_users", return_value=([user], None))

        items = user_service._filter_users({"username": user.username})

        assert items == [user]
        user_service._user_repository.filter_users.assert_called_once_with(
            filters={"username": user.username}, limit=100
        )

    def test_encode_next_key_successfully_returns_none_for_empty_key(self):
        encoded_next_key = UserService._encode_next_key(None)

        assert encoded_next_key is None

    def test_encode_next_key_successfully_returns_encoded_value(self):
        encoded_next_key = UserService._encode_next_key({"id": "next-page"})

        assert encoded_next_key == "eyJpZCI6Im5leHQtcGFnZSJ9"

    def test_decode_next_key_successfully_returns_none_for_empty_key(self):
        decoded_next_key = UserService._decode_next_key(None)

        assert decoded_next_key is None

    def test_decode_next_key_successfully_returns_decoded_value(self):
        decoded_next_key = UserService._decode_next_key("eyJpZCI6Im5leHQtcGFnZSJ9")

        assert decoded_next_key == {"id": "next-page"}

    def test_decode_next_key_raises_value_error_for_invalid_payload(self):
        invalid_next_key = urlsafe_b64encode(json.dumps(["invalid"]).encode()).decode()

        with pytest.raises(
            InvalidPaginationKeyException, match="Invalid pagination key"
        ):
            UserService._decode_next_key(invalid_next_key)

    def test_decode_next_key_raises_value_error_for_malformed_key(self):
        with pytest.raises(
            InvalidPaginationKeyException, match="Invalid pagination key"
        ):
            UserService._decode_next_key("asdasdasd")

    def test_successfully_create_user(self, mocker, user_service: UserService):
        mocker.patch.object(UserRepository, "get_user_by_email", return_value=None)
        mocker.patch.object(UserRepository, "get_by_username", return_value=None)
        create_user_mock = mocker.patch.object(UserRepository, "create_user")

        created_user_id = user_service.create_user(
            email="newuser@squarelabs.hu",
            password="not_so_secure_password",
            username="newuser",
            display_name="new_user",
        )

        assert isinstance(uuid.UUID(created_user_id), uuid.UUID)
        create_user_mock.assert_called_once()
        payload = create_user_mock.call_args.args[0]

        assert payload["id"] == created_user_id
        assert payload["display_name"] == "new_user"
        assert payload["email"] == "newuser@squarelabs.hu"
        assert payload["username"] == "newuser"
        assert payload["roles"] == []
        assert datetime.fromisoformat(payload["created_at"])
        assert payload["password"] != "not_so_secure_password"
        assert PasswordHasher().verify(payload["password"], "not_so_secure_password")

    def test_create_user_successfully_defaults_display_name_to_empty_string(
        self, mocker, user_service: UserService
    ):
        mocker.patch.object(UserRepository, "get_user_by_email", return_value=None)
        mocker.patch.object(UserRepository, "get_by_username", return_value=None)
        create_user_mock = mocker.patch.object(UserRepository, "create_user")

        user_service.create_user(
            email="newuser@squarelabs.hu",
            password="not_so_secure_password",
            username="newuser",
            display_name=None,
        )

        payload = create_user_mock.call_args.args[0]

        assert payload["display_name"] == ""

    def test_create_user_logs_warnings_when_user_already_exists(
        self, mocker, user: User, user_service: UserService
    ):
        mocker.patch.object(UserRepository, "get_user_by_email", return_value=user)
        mocker.patch.object(UserRepository, "get_by_username", return_value=user)
        mocker.patch.object(UserRepository, "create_user")
        logger_warning = mocker.patch.object(user_service._logger, "warning")

        user_service.create_user(
            email=user.email,
            password="not_so_secure_password",
            username=user.username,
            display_name=user.display_name,
        )

        assert logger_warning.call_count == 2

    def test_successfully_delete_user_by_id(
        self, mocker, user: User, user_service: UserService
    ):
        delete_user_mock = mocker.patch.object(UserRepository, "delete_user")

        user_service.delete_user_by_id(user.id)

        delete_user_mock.assert_called_once_with(user.id)

    def test_successfully_get_user_by_id(
        self, mocker, user: User, user_service: UserService
    ):
        get_by_id_mock = mocker.patch.object(
            UserRepository, "get_by_id", return_value=user
        )

        item = user_service.get_user_by_id(user.id)

        assert item == user
        get_by_id_mock.assert_called_once_with(user.id)

    def test_successfully_get_users_with_filters(
        self, mocker, user: User, user_service: UserService
    ):
        filter_users_mock = mocker.patch.object(
            UserRepository,
            "filter_users",
            return_value=(
                [user],
                {"id": "next-page"},
            ),
        )

        response = user_service.get_users(
            filters={"username": user.username},
            limit=10,
            next_key="eyJpZCI6ImN1cnJlbnQtcGFnZSJ9",
        )

        assert response == ([user], "eyJpZCI6Im5leHQtcGFnZSJ9")
        filter_users_mock.assert_called_once_with(
            filters={"username": user.username},
            limit=10,
            exclusive_start_key={"id": "current-page"},
        )

    def test_successfully_get_users_without_filters(
        self, mocker, user: User, user_service: UserService
    ):
        get_users_mock = mocker.patch.object(
            UserRepository, "get_users", return_value=([user], None)
        )

        response = user_service.get_users(filters=None, limit=10, next_key=None)

        assert response == ([user], None)
        get_users_mock.assert_called_once_with(
            limit=10,
            exclusive_start_key=None,
        )

    def test_successfully_update_user_by_id(
        self, mocker, user: User, user_service: UserService
    ):
        update_user_mock = mocker.patch.object(UserRepository, "update_user")

        user_service.update_user_by_id(
            user.id,
            {"display_name": "updated_root", "email": "updated@squarelabs.hu"},
        )

        update_user_mock.assert_called_once()
        called_user_id = update_user_mock.call_args.args[0]
        payload = update_user_mock.call_args.args[1]

        assert called_user_id == user.id
        assert payload["display_name"] == "updated_root"
        assert payload["email"] == "updated@squarelabs.hu"
        assert datetime.fromisoformat(payload["updated_at"])

    def test_successfully_validate_user_by_id(
        self, mocker, user: User, user_service: UserService
    ):
        mocker.patch.object(UserRepository, "get_by_id", return_value=user)
        mocker.patch.object(UserRepository, "update_user")
        mocker.patch.object(PasswordHasher, "verify", return_value=True)

        result = user_service.validate_user_by_id(user.id, "not_so_secure_password")

        assert result == user
        user_service._user_repository.get_by_id.assert_called_once_with(user.id)
        user_service._password_hasher.verify.assert_called_once_with(
            user.password, "not_so_secure_password"
        )

    def test_validate_user_by_id_raises_user_not_found_exception(
        self, mocker, user: User, user_service: UserService
    ):
        mocker.patch.object(UserRepository, "get_by_id", return_value=None)

        with pytest.raises(UserNotFoundException):
            user_service.validate_user_by_id(user.id, "not_so_secure_password")

    def test_validate_user_by_id_raises_invalid_password_exception(
        self, mocker, user: User, user_service: UserService
    ):
        mocker.patch.object(UserRepository, "get_by_id", return_value=user)
        mocker.patch.object(PasswordHasher, "verify", side_effect=VerifyMismatchError)

        with pytest.raises(InvalidPasswordException):
            user_service.validate_user_by_id(user.id, "wrong_password")
