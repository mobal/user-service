import json
import uuid
from base64 import urlsafe_b64decode, urlsafe_b64encode
from binascii import Error as BinasciiError
from datetime import UTC, datetime
from typing import Any

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from aws_lambda_powertools import Logger
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


class UserService:
    _ERROR_MESSAGE_INVALID_PAGINATION_KEY = "Invalid pagination key"
    _PAGINATION_KEY_FIELDS: set[str] = {"id"}
    _SYSTEM_UPDATE_FIELDS: set[str] = {"last_login_at", "deleted_at"}
    _USER_UPDATE_FIELDS: set[str] = {"display_name", "email", "username"}

    def __init__(
        self,
        user_repository: UserRepository | None = None,
        password_hasher: PasswordHasher | None = None,
        logger: Logger | None = None,
    ):
        self._logger = logger or Logger()
        self._password_hasher = password_hasher or PasswordHasher()
        self._user_repository = user_repository or UserRepository()

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(UTC).isoformat()

    @classmethod
    def _validate_next_key(cls, key: dict[str, Any]) -> dict[str, str]:
        if set(key) != cls._PAGINATION_KEY_FIELDS:
            raise InvalidPaginationKeyException(
                cls._ERROR_MESSAGE_INVALID_PAGINATION_KEY
            )

        key_id = key.get("id")
        if not isinstance(key_id, str) or not key_id:
            raise InvalidPaginationKeyException(
                cls._ERROR_MESSAGE_INVALID_PAGINATION_KEY
            )

        return {"id": key_id}

    @staticmethod
    def _assert_allowed_update_fields(
        user_data: dict[str, Any], allowed_fields: set[str]
    ) -> None:
        invalid_fields = set(user_data) - allowed_fields
        if invalid_fields:
            invalid_field_names = ", ".join(sorted(invalid_fields))
            raise BadRequestException(
                f"Invalid user update fields: {invalid_field_names}"
            )

    def _assert_user_does_not_exist(self, email: str, username: str) -> None:
        if self._user_repository.get_user_by_email(email):
            self._logger.warning(
                "User with email already exists",
                extra={"email": email},
            )
            raise UserAlreadyExistsException(f"User with email {email} already exists")

        if self._user_repository.get_by_username(username):
            self._logger.warning(
                "User with username already exists",
                extra={"username": username},
            )
            raise UserAlreadyExistsException(
                f"User with username {username} already exists"
            )

    def _assert_unique_user_identity(
        self, current_user: User, email: str | None, username: str | None
    ) -> None:
        if email and email != current_user.email:
            existing_user = self._user_repository.get_user_by_email(email)
            if existing_user and existing_user.id != current_user.id:
                raise UserAlreadyExistsException(
                    f"User with email {email} already exists"
                )

        if username and username != current_user.username:
            existing_user = self._user_repository.get_by_username(username)
            if existing_user and existing_user.id != current_user.id:
                raise UserAlreadyExistsException(
                    f"User with username {username} already exists"
                )

    def _update_user(
        self, user_id: str, user_data: dict[str, Any], allowed_fields: set[str]
    ) -> dict[str, Any]:
        self._assert_allowed_update_fields(user_data, allowed_fields)
        payload = {**user_data, "updated_at": self._now_iso()}

        try:
            return self._user_repository.update_user(user_id, payload)
        except ClientError as error:
            raise UserNotFoundException(f"User with id {user_id} not found") from error

    @staticmethod
    def _encode_next_key(next_key: dict[str, Any] | None) -> str | None:
        if not next_key:
            return None
        payload = json.dumps(next_key, separators=(",", ":")).encode("utf-8")
        return urlsafe_b64encode(payload).decode("utf-8")

    @classmethod
    def _decode_next_key(cls, next_key: str | None) -> dict[str, Any] | None:
        if not next_key:
            return None

        try:
            key = json.loads(
                urlsafe_b64decode(
                    (next_key + ("=" * (-len(next_key) % 4))).encode("utf-8")
                ).decode("utf-8")
            )
        except (BinasciiError, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise InvalidPaginationKeyException(
                cls._ERROR_MESSAGE_INVALID_PAGINATION_KEY
            ) from error

        if not isinstance(key, dict):
            raise InvalidPaginationKeyException(
                cls._ERROR_MESSAGE_INVALID_PAGINATION_KEY
            )

        return cls._validate_next_key(key)

    def create_user(
        self, email: str, password: str, username: str, display_name: str | None
    ) -> str:
        self._logger.info(
            "Creating user",
            extra={"email": email, "username": username, "display_name": display_name},
        )

        normalized_email = email.lower()
        self._assert_user_does_not_exist(normalized_email, username)
        user = User(
            id=str(uuid.uuid4()),
            email=normalized_email,
            password=self._password_hasher.hash(password),
            display_name=display_name or "",
            username=username,
            created_at=self._now_iso(),
        )

        self._user_repository.create_user(user.model_dump(exclude_none=True))

        return user.id

    def delete_user_by_id(self, user_id: str) -> dict[str, Any]:
        deleted_at = self._now_iso()
        try:
            return self._user_repository.delete_user(user_id, deleted_at)
        except ClientError as error:
            raise UserNotFoundException(f"User with id {user_id} not found") from error

    def get_user_by_id(self, user_id: str) -> User:
        user = self._user_repository.get_by_id(user_id)
        if not user:
            raise UserNotFoundException(f"User with id {user_id} not found")

        return user

    def get_users(
        self, filters: dict[str, str] | None, limit: int, next_key: str | None
    ) -> tuple[list[User], str | None]:
        exclusive_start_key = self._decode_next_key(next_key)

        if filters:
            users, last_evaluated_key = self._user_repository.filter_users(
                filters=filters,
                limit=limit,
                exclusive_start_key=exclusive_start_key,
            )
        else:
            users, last_evaluated_key = self._user_repository.get_users(
                limit=limit,
                exclusive_start_key=exclusive_start_key,
            )

        return users, self._encode_next_key(last_evaluated_key)

    def update_user_by_id(
        self, user_id: str, user_data: dict[str, Any]
    ) -> dict[str, Any]:
        user = self.get_user_by_id(user_id)
        normalized_data = dict(user_data)
        if "email" in normalized_data and normalized_data["email"] is not None:
            normalized_data["email"] = normalized_data["email"].lower()

        self._assert_unique_user_identity(
            current_user=user,
            email=normalized_data.get("email"),
            username=normalized_data.get("username"),
        )
        return self._update_user(
            user_id=user_id,
            user_data=normalized_data,
            allowed_fields=self._USER_UPDATE_FIELDS,
        )

    def validate_user_by_id(self, user_id: str, password: str) -> User:
        user = self.get_user_by_id(user_id)

        try:
            self._password_hasher.verify(user.password, password)
            if self._password_hasher.check_needs_rehash(user.password):
                self._update_user(
                    user_id=user_id,
                    user_data={"password": self._password_hasher.hash(password)},
                    allowed_fields=self._USER_UPDATE_FIELDS | {"password"},
                )
            self._logger.info(
                "User authenticated successfully",
                extra={"user_id": user_id},
            )

            updated_user = self._update_user(
                user_id=user_id,
                user_data={"last_login_at": self._now_iso()},
                allowed_fields=self._SYSTEM_UPDATE_FIELDS,
            )
            return User(**updated_user)
        except (VerificationError, InvalidHashError) as error:
            raise InvalidPasswordException("Invalid password") from error
