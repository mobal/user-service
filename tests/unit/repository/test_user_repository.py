import uuid
from datetime import UTC, datetime
from typing import Any

import pytest
from botocore.exceptions import ClientError

from app.models.user import User
from app.repositories.user_repository import UserRepository


class TestUserRepository:
    @pytest.fixture
    def user_repository(self) -> UserRepository:
        return UserRepository()

    def test_successfully_create_user(
        self, user: User, user_repository: UserRepository, users_table
    ):
        new_user_id = str(uuid.uuid4())
        user_data = {
            "id": new_user_id,
            "display_name": "new_user",
            "email": "newuser@squarelabs.hu",
            "password": "hashed_password",
            "username": "newuser",
            "created_at": datetime.now(UTC).isoformat(),
        }
        user_repository.create_user(user_data)

        response = users_table.get_item(Key={"id": new_user_id})

        assert response["Item"] == user_data

    def test_successfully_delete_user(
        self, user: User, user_repository: UserRepository, users_table
    ):
        deleted_at = datetime.now(UTC).isoformat()
        response = user_repository.delete_user(user.id, deleted_at)
        item = users_table.get_item(Key={"id": user.id})["Item"]

        assert response["id"] == user.id
        assert response["deleted_at"] == deleted_at
        assert item["deleted_at"] == deleted_at

    def test_delete_user_raises_when_id_not_found(
        self, user_repository: UserRepository, users_table
    ):
        with pytest.raises(ClientError) as error:
            user_repository.delete_user(
                str(uuid.uuid4()), datetime.now(UTC).isoformat()
            )

        assert (
            error.value.response.get("Error", {}).get("Code")
            == "ConditionalCheckFailedException"
        )

    def test_successfully_get_by_id(
        self, users_table, user: User, user_repository: UserRepository
    ):
        item = user_repository.get_by_id(user.id)

        assert user == item

    def test_successfully_return_none_by_id(
        self, users_table, user_repository: UserRepository
    ):
        item = user_repository.get_by_id(str(uuid.uuid4()))

        assert item is None

    def test_successfully_get_by_username(
        self, users_table, user: User, user_repository: UserRepository
    ):
        item = user_repository.get_by_username(user.username)

        assert user == item

    def test_successfully_return_none_by_username(
        self, users_table, user_repository: UserRepository
    ):
        item = user_repository.get_by_username("nonexistentuser")

        assert item is None

    def test_successfully_get_user_by_email(
        self, users_table, user: User, user_repository: UserRepository
    ):
        item = user_repository.get_user_by_email(user.email)

        assert user == item

    def test_successfully_return_none_by_email(
        self, users_table, user_repository: UserRepository
    ):
        item = user_repository.get_user_by_email("nonexistentuser@squarelabs.hu")

        assert item is None

    def test_get_user_by_email_returns_none_for_soft_deleted_user(
        self, users_table, user: User, user_repository: UserRepository
    ):
        deleted_at = datetime.now(UTC).isoformat()
        users_table.update_item(
            Key={"id": user.id},
            UpdateExpression="SET deleted_at = :deleted_at",
            ExpressionAttributeValues={":deleted_at": deleted_at},
        )

        item = user_repository.get_user_by_email(user.email)

        assert item is None

    def test_successfully_update_user(
        self, users_table, user: User, user_repository: UserRepository
    ):
        updated_at = datetime.now(UTC).isoformat()

        response = user_repository.update_user(
            user.id,
            {
                "id": str(uuid.uuid4()),
                "display_name": "updated_root",
                "updated_at": updated_at,
            },
        )

        item = users_table.get_item(Key={"id": user.id})["Item"]

        assert response["id"] == user.id
        assert item["id"] == user.id
        assert response["display_name"] == "updated_root"
        assert item["display_name"] == "updated_root"
        assert response["updated_at"] == updated_at
        assert item["updated_at"] == updated_at

    def test_update_user_returns_empty_dict_when_only_id_is_provided(
        self, user: User, user_repository: UserRepository
    ):
        response = user_repository.update_user(user.id, {"id": user.id})

        assert response == {}

    def test_update_user_raises_when_id_not_found(
        self, user_repository: UserRepository, users_table
    ):
        with pytest.raises(ClientError) as error:
            user_repository.update_user(
                str(uuid.uuid4()),
                {
                    "display_name": "updated_root",
                    "updated_at": datetime.now(UTC).isoformat(),
                },
            )

        assert (
            error.value.response.get("Error", {}).get("Code")
            == "ConditionalCheckFailedException"
        )

    def test_filter_users_returns_only_matching_active_users(
        self, users_table, user_repository: UserRepository
    ):
        created_at = datetime.now(UTC).isoformat()
        matching_user = {
            "id": str(uuid.uuid4()),
            "display_name": "filtered_user",
            "email": "filtered@squarelabs.hu",
            "password": "hashed_password",
            "username": "filtered_user",
            "roles": ["user"],
            "created_at": created_at,
        }
        deleted_user = {
            "id": str(uuid.uuid4()),
            "display_name": "filtered_user",
            "email": "deleted-filtered@squarelabs.hu",
            "password": "hashed_password",
            "username": "deleted_filtered_user",
            "roles": ["user"],
            "created_at": created_at,
            "deleted_at": created_at,
        }
        users_table.put_item(Item=matching_user)
        users_table.put_item(Item=deleted_user)

        items, next_key = user_repository.filter_users(
            {"display_name": "filtered_user"}, limit=10
        )

        assert items == [User(**matching_user)]
        assert next_key is None

    def test_filter_users_returns_empty_when_no_match(
        self, users_table, user_repository: UserRepository
    ):
        items, next_key = user_repository.filter_users(
            {"display_name": "nonexistent"}, limit=10
        )

        assert items == []
        assert next_key is None

    def test_filter_users_with_exclusive_start_key(
        self, users_table, user_repository: UserRepository
    ):
        created_at = datetime.now(UTC).isoformat()
        # Add two users matching the same filter
        user1 = {
            "id": str(uuid.uuid4()),
            "display_name": "filter_me",
            "email": "user1@squarelabs.hu",
            "password": "hashed_password",
            "username": "user1",
            "roles": ["user"],
            "created_at": created_at,
        }
        user2 = {
            "id": str(uuid.uuid4()),
            "display_name": "filter_me",
            "email": "user2@squarelabs.hu",
            "password": "hashed_password",
            "username": "user2",
            "roles": ["user"],
            "created_at": created_at,
        }
        users_table.put_item(Item=user1)
        users_table.put_item(Item=user2)

        # Collect all matching items across pages using exclusive_start_key.
        # DynamoDB applies Limit BEFORE FilterExpression, so we loop with a
        # generous limit per page and accumulate results until the table is exhausted.
        all_found: dict[str, User] = {}
        next_key: dict[str, Any] | None = None

        while True:
            items, next_key = user_repository.filter_users(
                {"display_name": "filter_me"},
                limit=10,
                exclusive_start_key=next_key,
            )
            for item in items:
                all_found[item.id] = item
            if not next_key:
                break

        assert len(all_found) == 2, f"Expected 2 matching users, got {len(all_found)}"
        assert user1["id"] in all_found
        assert user2["id"] in all_found

    def test_get_users_returns_only_active_users(
        self, users_table, user: User, user_repository: UserRepository
    ):
        deleted_user = {
            "id": str(uuid.uuid4()),
            "display_name": "deleted_user",
            "email": "deleted@squarelabs.hu",
            "password": "hashed_password",
            "username": "deleted_user",
            "roles": ["user"],
            "created_at": datetime.now(UTC).isoformat(),
            "deleted_at": datetime.now(UTC).isoformat(),
        }
        users_table.put_item(Item=deleted_user)

        items, next_key = user_repository.get_users(limit=10)

        assert user in items
        assert User(**deleted_user) not in items
        assert next_key is None

    def test_get_users_returns_empty_list_when_no_active_users(
        self, users_table, user: User, user_repository: UserRepository
    ):
        # Delete the seeded user so no active users remain
        users_table.delete_item(Key={"id": user.id})

        items, next_key = user_repository.get_users(limit=10)

        assert items == []
        assert next_key is None

    def test_get_users_with_exclusive_start_key(
        self, users_table, user: User, user_repository: UserRepository
    ):
        created_at = datetime.now(UTC).isoformat()
        second_user = {
            "id": str(uuid.uuid4()),
            "display_name": "second_user",
            "email": "second@squarelabs.hu",
            "password": "hashed_password",
            "username": "second_user",
            "roles": ["user"],
            "created_at": created_at,
        }
        users_table.put_item(Item=second_user)

        # Get first page
        items, next_key = user_repository.get_users(limit=1)

        assert len(items) == 1
        assert next_key is not None

        # Get second page
        items, next_key = user_repository.get_users(
            limit=10, exclusive_start_key=next_key
        )

        assert len(items) == 1
        assert next_key is None

    def test_get_by_id_returns_none_for_soft_deleted_user(
        self, users_table, user: User, user_repository: UserRepository
    ):
        """Test that get_by_id returns None for a soft-deleted user."""
        from datetime import UTC, datetime

        deleted_at = datetime.now(UTC).isoformat()
        users_table.update_item(
            Key={"id": user.id},
            UpdateExpression="SET deleted_at = :deleted_at",
            ExpressionAttributeValues={":deleted_at": deleted_at},
        )

        item = user_repository.get_by_id(user.id)

        assert item is None

    def test_get_by_username_returns_none_for_soft_deleted_user(
        self, users_table, user: User, user_repository: UserRepository
    ):
        """Test that get_by_username returns None for a soft-deleted user."""
        from datetime import UTC, datetime

        deleted_at = datetime.now(UTC).isoformat()
        users_table.update_item(
            Key={"id": user.id},
            UpdateExpression="SET deleted_at = :deleted_at",
            ExpressionAttributeValues={":deleted_at": deleted_at},
        )

        item = user_repository.get_by_username(user.username)

        assert item is None
