import json
import uuid
from base64 import urlsafe_b64decode, urlsafe_b64encode
from binascii import Error as BinasciiError
from datetime import UTC, datetime
from typing import Any

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from aws_lambda_powertools import Logger

from app.exceptions import (
    InvalidPaginationKeyException,
    InvalidPasswordException,
    UserNotFoundException,
)
from app.models.user import User
from app.repositories.user_repository import UserRepository


class UserService:
    def __init__(self):
        self._logger = Logger()
        self._password_hasher = PasswordHasher()
        self._user_repository = UserRepository()

    def _filter_users(self, filters: dict[str, str]) -> list[User]:
        users, _ = self._user_repository.filter_users(filters=filters, limit=100)
        return users

    @staticmethod
    def _encode_next_key(next_key: dict[str, Any] | None) -> str | None:
        if not next_key:
            return None
        payload = json.dumps(next_key, separators=(",", ":")).encode("utf-8")
        return urlsafe_b64encode(payload).decode("utf-8")

    @staticmethod
    def _decode_next_key(next_key: str | None) -> dict[str, Any] | None:
        if not next_key:
            return None

        try:
            key = json.loads(
                urlsafe_b64decode(
                    (next_key + ("=" * (-len(next_key) % 4))).encode("utf-8")
                ).decode("utf-8")
            )
        except (BinasciiError, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise InvalidPaginationKeyException("Invalid pagination key") from error

        if not isinstance(key, dict):
            raise InvalidPaginationKeyException("Invalid pagination key")

        return key

    def create_user(
        self, email: str, password: str, username: str, display_name: str | None
    ) -> User:
        self._logger.info(
            f"Creating user with email: {email}",
            extra={"email": email, "username": username, "display_name": display_name},
        )

        if self._user_repository.get_user_by_email(email):
            self._logger.warning(
                f"User with email {email} already exists", extra={"email": email}
            )
            raise UserNotFoundException(f"User with email {email} already exists")

        if self._user_repository.get_by_username(username):
            self._logger.warning(
                f"User with username {username} already exists",
                extra={"username": username},
            )

        user = User(
            id=str(uuid.uuid4()),
            email=email,
            password=self._password_hasher.hash(password),
            display_name=display_name or "",
            username=username,
            created_at=datetime.now(UTC).isoformat(),
        )

        self._user_repository.create_user(user.model_dump(exclude_none=True))

        return user.id

    def delete_user_by_id(self, user_id: str):
        self._user_repository.delete_user(user_id)

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
        payload = {**user_data, "updated_at": datetime.now(UTC).isoformat()}
        return self._user_repository.update_user(user_id, payload)

    def validate_user_by_id(self, user_id: str, password: str) -> User:
        user = self.get_user_by_id(user_id)

        try:
            self._password_hasher.verify(user.password, password)
            self._logger.info(
                f"User {user_id} authenticated successfully", extra={"user_id": user_id}
            )

            updated_user = self.update_user_by_id(
                user_id=user_id,
                user_data={"last_login_at": datetime.now(UTC).isoformat()},
            )
            return User(**updated_user)
        except VerifyMismatchError as error:
            raise InvalidPasswordException("Invalid password") from error
