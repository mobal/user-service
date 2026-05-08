from typing import Any

import boto3
from boto3.dynamodb.conditions import Attr, Key

from app import settings
from app.models.role import Role


class RoleRepository:
    def __init__(self):
        self._table = (
            boto3.Session().resource("dynamodb").Table(f"{settings.stage}-roles")
        )

    @staticmethod
    def _is_active(item: dict[str, Any] | None) -> bool:
        return bool(item) and item.get("deleted_at") is None

    @staticmethod
    def _extract_role_name(path: str) -> str:
        return path.rsplit("#", maxsplit=1)[-1].strip()

    def create_role(self, data: dict[str, Any]) -> dict[str, Any]:
        return self._table.put_item(Item=data)

    def delete_role(self, role_id: str) -> dict[str, Any]:
        return self._table.delete_item(Key={"id": role_id})

    def update_role(self, role_id: str, data: dict[str, Any]) -> dict[str, Any]:
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

        response = self._table.update_item(
            Key={"id": role_id},
            UpdateExpression=f"SET {', '.join(set_clauses)}",
            ExpressionAttributeNames=expression_names,
            ExpressionAttributeValues=expression_values,
            ReturnValues="ALL_NEW",
        )

        return response.get("Attributes", {})

    def get_by_id(self, role_id: str) -> Role | None:
        response = self._table.get_item(Key={"id": role_id})
        item = response.get("Item")
        if self._is_active(item):
            return Role(**item)
        return None

    def get_by_path(self, path: str) -> Role | None:
        response = self._table.query(
            IndexName="PathIndex",
            KeyConditionExpression=Key("path").eq(path),
            FilterExpression=Attr("deleted_at").not_exists()
            | Attr("deleted_at").eq(None),
        )
        if response["Items"]:
            return Role(**response["Items"][0])
        return None

    def get_by_name(self, role_name: str) -> Role | None:
        scan_kwargs: dict[str, Any] = {
            "FilterExpression": Attr("deleted_at").not_exists()
            | Attr("deleted_at").eq(None),
        }

        while True:
            response = self._table.scan(**scan_kwargs)
            for item in response.get("Items", []):
                if self._extract_role_name(item.get("path", "")) == role_name:
                    return Role(**item)

            last_evaluated_key = response.get("LastEvaluatedKey")
            if not last_evaluated_key:
                return None

            scan_kwargs["ExclusiveStartKey"] = last_evaluated_key
