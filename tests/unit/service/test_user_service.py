import json
import uuid
from base64 import urlsafe_b64encode
from datetime import datetime

import pytest
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from botocore.exceptions import ClientError

from app.exceptions import (
    BadRequestException,
    InvalidPaginationKeyException,
    InvalidPasswordException,
    UserAlreadyExistsException,
    UserNotFoundException,
)
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.services.user_service import UserService


class TestUserService:
    @pytest.fixture
    def user_service(self) -> UserService:
        return UserService()

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

    def test_decode_next_key_raises_value_error_for_wrong_shape(self):
        invalid_next_key = urlsafe_b64encode(
            json.dumps({"id": "next-page", "email": "user@example.com"}).encode()
        ).decode()

        with pytest.raises(
            InvalidPaginationKeyException, match="Invalid pagination key"
        ):
            UserService._decode_next_key(invalid_next_key)

    def test_validate_next_key_validates_only_id_field(
        self, mocker, user_service: UserService
    ):
        key = {"id": "some-id"}

        result = user_service._validate_next_key(key)

        assert result == {"id": "some-id"}

    def test_validate_next_key_rejects_empty_string_id(
        self, mocker, user_service: UserService
    ):
        """Test that empty string id in pagination key raises exception (line 53 coverage)."""
        with pytest.raises(
            InvalidPaginationKeyException,
            match="Invalid pagination key",
        ):
            user_service._validate_next_key({"id": ""})

    def test_validate_next_key_rejects_none_id(self, mocker, user_service: UserService):
        """Test that None id in pagination key raises exception (line 53 coverage)."""
        with pytest.raises(
            InvalidPaginationKeyException,
            match="Invalid pagination key",
        ):
            user_service._validate_next_key({"id": None})

    def test_validate_next_key_rejects_non_string_id(
        self, mocker, user_service: UserService
    ):
        """Test that non-string id in pagination key raises exception (line 53 coverage)."""
        with pytest.raises(
            InvalidPaginationKeyException,
            match="Invalid pagination key",
        ):
            user_service._validate_next_key({"id": 123})

    def test_create_user_omits_display_name_when_not_provided(
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

        assert "display_name" not in payload

    def test_create_user_normalizes_email_to_lowercase(
        self, mocker, user_service: UserService
    ):
        """Test that create_user lowercases the email (line 153 coverage)."""
        mocker.patch.object(UserRepository, "get_user_by_email", return_value=None)
        mocker.patch.object(UserRepository, "get_by_username", return_value=None)
        create_user_mock = mocker.patch.object(UserRepository, "create_user")

        user_service.create_user(
            email="UPPERCASE@SQUARELABS.HU",
            password="not_so_secure_password",
            username="newuser",
            display_name="Uppercase User",
        )

        payload = create_user_mock.call_args.args[0]

        assert payload["email"] == "uppercase@squarelabs.hu"

    def test_create_user_raises_conflict_when_email_already_exists(
        self, mocker, user: User, user_service: UserService
    ):
        mocker.patch.object(UserRepository, "get_user_by_email", return_value=user)
        create_user_mock = mocker.patch.object(UserRepository, "create_user")
        logger_warning = mocker.patch.object(user_service._logger, "warning")

        with pytest.raises(UserAlreadyExistsException):
            user_service.create_user(
                email=user.email,
                password="not_so_secure_password",
                username="different_username",
                display_name=user.display_name,
            )

        create_user_mock.assert_not_called()
        logger_warning.assert_called_once()

    def test_create_user_raises_conflict_when_username_already_exists(
        self, mocker, user: User, user_service: UserService
    ):
        mocker.patch.object(UserRepository, "get_user_by_email", return_value=None)
        mocker.patch.object(UserRepository, "get_by_username", return_value=user)

        with pytest.raises(UserAlreadyExistsException):
            user_service.create_user(
                email="new@example.com",
                password="not_so_secure_password",
                username=user.username,
                display_name=user.display_name,
            )

    def test_delete_user_by_id_soft_deletes_user(
        self, mocker, user: User, user_service: UserService
    ):
        delete_user_mock = mocker.patch.object(
            UserRepository, "delete_user", return_value=user.model_dump()
        )

        user_service.delete_user_by_id(user.id)

        delete_user_mock.assert_called_once()
        called_user_id = delete_user_mock.call_args.args[0]
        deleted_at = delete_user_mock.call_args.args[1]

        assert called_user_id == user.id
        assert datetime.fromisoformat(deleted_at)

    def test_delete_user_by_id_raises_user_not_found_exception(
        self, mocker, user: User, user_service: UserService
    ):
        """Test that delete_user_by_id raises UserNotFoundException when user not found (lines 172-173 coverage)."""
        delete_user_mock = mocker.patch.object(
            UserRepository,
            "delete_user",
            side_effect=ClientError(
                {
                    "Error": {
                        "Code": "ConditionalCheckFailedException",
                        "Message": "User not found",
                    }
                },
                "DeleteUser",
            ),
        )

        with pytest.raises(UserNotFoundException, match="User with id .* not found"):
            user_service.delete_user_by_id(user.id)

        delete_user_mock.assert_called_once()

    def test_successfully_get_user_by_id(
        self, mocker, user: User, user_service: UserService
    ):
        get_by_id_mock = mocker.patch.object(
            UserRepository, "get_by_id", return_value=user
        )

        item = user_service.get_user_by_id(user.id)

        assert item == user
        get_by_id_mock.assert_called_once_with(user.id)

    def test_get_user_by_id_raises_not_found_when_user_missing(
        self, mocker, user_service: UserService
    ):
        """Test that get_user_by_id raises UserNotFoundException when user not found (lines 177-178 coverage)."""
        mocker.patch.object(UserRepository, "get_by_id", return_value=None)

        with pytest.raises(UserNotFoundException, match="User with id .* not found"):
            user_service.get_user_by_id("nonexistent-id")

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
            next_key="eyJpZCI6Im5leHQtcGFnZSJ9",
        )

        assert response == ([user], "eyJpZCI6Im5leHQtcGFnZSJ9")
        filter_users_mock.assert_called_once_with(
            filters={"username": user.username},
            limit=10,
            exclusive_start_key={"id": "next-page"},
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

    def test_get_users_uses_scan_when_filters_is_empty_dict(
        self, mocker, user: User, user_service: UserService
    ):
        """Test that empty dict filters falls through to get_users (line 187: empty dict is falsy)."""
        get_users_mock = mocker.patch.object(
            UserRepository, "get_users", return_value=([user], None)
        )
        filter_users_mock = mocker.patch.object(UserRepository, "filter_users")

        response = user_service.get_users(filters={}, limit=10, next_key=None)

        assert response == ([user], None)
        get_users_mock.assert_called_once()
        filter_users_mock.assert_not_called()

    def test_get_users_returns_no_users_when_table_empty(
        self, mocker, user_service: UserService
    ):
        """Test get_users with empty results."""
        mocker.patch.object(UserRepository, "get_users", return_value=([], None))

        response = user_service.get_users(filters=None, limit=10, next_key=None)

        assert response == ([], None)

    def test_successfully_update_user_by_id(
        self, mocker, user: User, user_service: UserService
    ):
        mocker.patch.object(UserRepository, "get_by_id", return_value=user)
        mocker.patch.object(UserRepository, "get_user_by_email", return_value=None)
        mocker.patch.object(UserRepository, "get_by_username", return_value=None)
        update_user_mock = mocker.patch.object(
            UserRepository, "update_user", return_value=user.model_dump()
        )

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

    def test_update_user_by_id_raises_for_invalid_fields(
        self, mocker, user: User, user_service: UserService
    ):
        mocker.patch.object(UserRepository, "get_by_id", return_value=user)

        with pytest.raises(BadRequestException):
            user_service.update_user_by_id(user.id, {"roles": ["admin"]})

    def test_update_user_by_id_normalizes_email_to_lowercase(
        self, mocker, user: User, user_service: UserService
    ):
        """Test that update_user_by_id lowercases the email (line 207 coverage)."""
        mocker.patch.object(UserRepository, "get_by_id", return_value=user)
        mocker.patch.object(UserRepository, "get_user_by_email", return_value=None)
        mocker.patch.object(UserRepository, "get_by_username", return_value=None)
        update_user_mock = mocker.patch.object(
            UserRepository, "update_user", return_value=user.model_dump()
        )

        user_service.update_user_by_id(
            user.id,
            {"email": "MIXEDCASE@SQUARELABS.HU"},
        )

        payload = update_user_mock.call_args.args[1]
        assert payload["email"] == "mixedcase@squarelabs.hu"

    def test_update_user_by_id_does_not_raise_when_email_is_same(
        self, mocker, user: User, user_service: UserService
    ):
        """Test that update_user_by_id does not raise when updating to the same email."""
        mocker.patch.object(UserRepository, "get_by_id", return_value=user)
        # get_user_by_email returns the same user (which is fine as id matches)
        mocker.patch.object(UserRepository, "get_user_by_email", return_value=user)
        mocker.patch.object(UserRepository, "get_by_username", return_value=None)
        update_user_mock = mocker.patch.object(
            UserRepository, "update_user", return_value=user.model_dump()
        )

        user_service.update_user_by_id(
            user.id,
            {"display_name": "updated_root"},
        )

        update_user_mock.assert_called_once()

    def test_update_user_by_id_does_not_raise_when_username_is_same(
        self, mocker, user: User, user_service: UserService
    ):
        """Test that update_user_by_id does not raise when updating to the same username."""
        mocker.patch.object(UserRepository, "get_by_id", return_value=user)
        mocker.patch.object(UserRepository, "get_user_by_email", return_value=None)
        # get_by_username returns the same user (which is fine as id matches)
        mocker.patch.object(UserRepository, "get_by_username", return_value=user)
        update_user_mock = mocker.patch.object(
            UserRepository, "update_user", return_value=user.model_dump()
        )

        user_service.update_user_by_id(
            user.id,
            {"display_name": "updated_root"},
        )

        update_user_mock.assert_called_once()

    def test_update_user_by_id_raises_when_email_belongs_to_other_user(
        self, mocker, user: User, user_service: UserService
    ):
        other_user = user.model_copy(
            update={"id": str(uuid.uuid4()), "email": "other@squarelabs.hu"}
        )
        mocker.patch.object(UserRepository, "get_by_id", return_value=user)
        mocker.patch.object(
            UserRepository, "get_user_by_email", return_value=other_user
        )

        with pytest.raises(UserAlreadyExistsException):
            user_service.update_user_by_id(user.id, {"email": other_user.email})

    def test_update_user_by_id_raises_when_username_belongs_to_other_user(
        self, mocker, user: User, user_service: UserService
    ):
        """Test that update_user_by_id raises when username belongs to another user (lines 98-100 coverage)."""
        other_user = user.model_copy(
            update={"id": str(uuid.uuid4()), "username": "different_username"}
        )
        mocker.patch.object(UserRepository, "get_by_id", return_value=user)
        mocker.patch.object(UserRepository, "get_by_username", return_value=other_user)

        with pytest.raises(UserAlreadyExistsException):
            user_service.update_user_by_id(user.id, {"username": "different_username"})

    def test_update_user_by_id_raises_user_not_found_when_update_fails(
        self, mocker, user: User, user_service: UserService
    ):
        """Test that update_user_by_id raises UserNotFoundException when update_user fails (lines 112-113 coverage)."""
        mocker.patch.object(UserRepository, "get_by_id", return_value=user)
        update_user_mock = mocker.patch.object(
            UserRepository,
            "update_user",
            side_effect=ClientError(
                {
                    "Error": {
                        "Code": "ConditionalCheckFailedException",
                        "Message": "User not found",
                    }
                },
                "UpdateItem",
            ),
        )

        with pytest.raises(UserNotFoundException, match="User with id .* not found"):
            user_service.update_user_by_id(user.id, {"display_name": "updated"})

        update_user_mock.assert_called_once()

    def test_successfully_validate_user_by_id(
        self, mocker, user: User, user_service: UserService
    ):
        mocker.patch.object(UserRepository, "get_by_id", return_value=user)
        mocker.patch.object(
            UserRepository, "update_user", return_value=user.model_dump()
        )
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

    def test_validate_user_by_id_raises_invalid_password_for_invalid_hash(
        self, mocker, user: User, user_service: UserService
    ):
        mocker.patch.object(UserRepository, "get_by_id", return_value=user)
        mocker.patch.object(PasswordHasher, "verify", side_effect=InvalidHashError)

        with pytest.raises(InvalidPasswordException):
            user_service.validate_user_by_id(user.id, "wrong_password")

    def test_validate_user_by_id_raises_not_found_for_deleted_user(
        self, mocker, user: User, user_service: UserService
    ):
        """Test that validate_user_by_id raises UserNotFoundException when user is soft-deleted (L8)."""
        mocker.patch.object(UserRepository, "get_by_id", return_value=None)

        with pytest.raises(UserNotFoundException, match="User with id .* not found"):
            user_service.validate_user_by_id(user.id, "not_so_secure_password")

    def test_validate_user_by_id_triggers_password_rehash_when_needed(
        self, mocker, user: User, user_service: UserService
    ):
        """Test that validate_user_by_id updates password when rehash is needed (line 226 coverage)."""
        user_data = user.model_dump()
        mocker.patch.object(UserRepository, "get_by_id", return_value=user)
        update_user_mock = mocker.patch.object(
            UserRepository, "update_user", return_value=user_data
        )
        mocker.patch.object(PasswordHasher, "verify", return_value=True)
        mocker.patch.object(PasswordHasher, "check_needs_rehash", return_value=True)

        user_service.validate_user_by_id(user.id, "not_so_secure_password")

        assert update_user_mock.call_count == 1
        # Single call should include both password and last_login_at update

    def test_validate_user_by_id_without_password_rehash(
        self, mocker, user: User, user_service: UserService
    ):
        user_data = user.model_dump()
        mocker.patch.object(UserRepository, "get_by_id", return_value=user)
        update_user_mock = mocker.patch.object(
            UserRepository, "update_user", return_value=user_data
        )
        mocker.patch.object(PasswordHasher, "verify", return_value=True)
        mocker.patch.object(PasswordHasher, "check_needs_rehash", return_value=False)

        user_service.validate_user_by_id(user.id, "not_so_secure_password")

        assert update_user_mock.call_count == 1

    def test_encode_next_key_returns_none_for_empty_dict(
        self, user_service: UserService
    ):
        """Test encoding an empty dict — empty dict is falsy so returns None."""
        encoded_next_key = UserService._encode_next_key({})

        assert encoded_next_key is None

    def test_decode_next_key_raises_for_non_dict_json(self, user_service: UserService):
        """Test decoding valid JSON that is not a dict."""
        from base64 import urlsafe_b64encode

        encoded = urlsafe_b64encode(b'"string_value"').decode()

        with pytest.raises(
            InvalidPaginationKeyException, match="Invalid pagination key"
        ):
            UserService._decode_next_key(encoded)

    def test_create_user_raises_user_already_exists_with_email_first(
        self, mocker, user: User, user_service: UserService
    ):
        """Test that email conflict is checked before username conflict."""
        mocker.patch.object(UserRepository, "get_user_by_email", return_value=user)
        get_by_username_mock = mocker.patch.object(
            UserRepository, "get_by_username", return_value=None
        )

        with pytest.raises(
            UserAlreadyExistsException, match="User with email .* already exists"
        ):
            user_service.create_user(
                email=user.email,
                password="not_so_secure_password",
                username="new_username",
                display_name=None,
            )

        get_by_username_mock.assert_not_called()
