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

    def delete_user(self, user_id: int) -> dict[str, Any]:
        return self._table.delete_item(Key={"user_id": user_id})

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
