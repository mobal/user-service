from typing import Any

import boto3
from boto3.dynamodb.conditions import Attr, Key

from app import settings
from app.models.user import User


class UserRepository:
    def __init__(self):
        self._table = (
            boto3.Session().resource("dynamodb").Table(f"{settings.stage}-users")
        )

    def create_user(self, data: dict[str, Any]) -> dict[str, Any]:
        return self._table.put_item(Item=data)

    def delete_user(self, user_id: str) -> dict[str, Any]:
        return self._table.delete_item(Key={"id": user_id})

    def filter_users(
        self,
        filters: dict[str, str],
        limit: int,
        exclusive_start_key: dict[str, Any] | None = None,
    ) -> tuple[list[User], dict[str, Any] | None]:
        filter_expression = Attr("deleted_at").not_exists() | Attr("deleted_at").eq(
            None
        )
        for key, value in filters.items():
            condition = Attr(key).eq(value)
            filter_expression = filter_expression & condition

        scan_kwargs: dict[str, Any] = {
            "FilterExpression": filter_expression,
            "Limit": limit,
        }
        if exclusive_start_key:
            scan_kwargs["ExclusiveStartKey"] = exclusive_start_key

        response = self._table.scan(**scan_kwargs)
        users = [User(**item) for item in response.get("Items", [])]
        return users, response.get("LastEvaluatedKey")

    def get_users(
        self, limit: int, exclusive_start_key: dict[str, Any] | None = None
    ) -> tuple[list[User], dict[str, Any] | None]:
        filter_expression = Attr("deleted_at").not_exists() | Attr("deleted_at").eq(
            None
        )

        scan_kwargs: dict[str, Any] = {
            "FilterExpression": filter_expression,
            "Limit": limit,
        }
        if exclusive_start_key:
            scan_kwargs["ExclusiveStartKey"] = exclusive_start_key

        response = self._table.scan(**scan_kwargs)
        users = [User(**item) for item in response.get("Items", [])]
        return users, response.get("LastEvaluatedKey")

    def update_user(self, user_id: str, data: dict[str, Any]) -> dict[str, Any]:
        update_data = {k: v for k, v in data.items() if k != "id"}
        if not update_data:
            return {}

        expression_names: dict[str, str] = {}
        expression_values: dict[str, Any] = {}
        set_clauses: list[str] = []

        for index, (key, value) in enumerate(update_data.items()):
            name_key = f"#f{index}"
            value_key = f":v{index}"
            expression_names[name_key] = key
            expression_values[value_key] = value
            set_clauses.append(f"{name_key} = {value_key}")

        return self._table.update_item(
            Key={"id": user_id},
            UpdateExpression=f"SET {', '.join(set_clauses)}",
            ExpressionAttributeNames=expression_names,
            ExpressionAttributeValues=expression_values,
        )

    def get_user_by_email(self, email: str) -> User | None:
        response = self._table.query(
            IndexName="EmailIndex",
            KeyConditionExpression=Key("email").eq(email),
            FilterExpression=Attr("deleted_at").not_exists()
            | Attr("deleted_at").eq(None),
        )
        if response["Items"]:
            return User(**response["Items"][0])
        return None

    def get_by_id(self, user_id: int) -> User | None:
        response = self._table.query(
            KeyConditionExpression=Key("id").eq(user_id),
            FilterExpression=Attr("deleted_at").not_exists()
            | Attr("deleted_at").eq(None),
        )
        if response["Items"]:
            return User(**response["Items"][0])
        return None

    def get_by_username(self, username: str) -> User | None:
        response = self._table.query(
            IndexName="UsernameIndex",
            KeyConditionExpression=Key("username").eq(username),
            FilterExpression=Attr("deleted_at").not_exists()
            | Attr("deleted_at").eq(None),
        )
        if response["Items"]:
            return User(**response["Items"][0])
        return None
