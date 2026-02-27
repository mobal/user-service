import uuid
from datetime import UTC, datetime

from argon2 import PasswordHasher
from aws_lambda_powertools import Logger

from app.models.user import User
from app.repositories.user_repository import UserRepository


class UserService:
    def __init__(self):
        self._logger = Logger()
        self._password_hasher = PasswordHasher()
        self._user_repository = UserRepository()

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

    def delete_user_by_id(self, user_id: int):
        self._user_repository.delete_user(user_id)

    def get_user_by_id(self, user_id: int) -> User | None:
        return self._user_repository.get_by_id(user_id)

    def get_users(self) -> list[User]:
        return self._user_repository.get_users()

    def update_user_by_id(self, user_id: int, user_data: dict):
        self._user_repository.update_user(user_id, user_data)
