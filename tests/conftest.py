import os
import uuid
from datetime import UTC, datetime
from typing import Any

import boto3
import pytest
from argon2 import PasswordHasher
from moto import mock_aws

from app.models.user import User
from app.settings import Settings


@pytest.fixture(autouse=True)
def setup(monkeypatch):
    with mock_aws():
        monkeypatch.setenv(
            "JWT_SECRET_SSM_PARAM_NAME", os.getenv("JWT_SECRET_SSM_PARAM_NAME")
        )
        ssm_client = boto3.client(
            "ssm",
            region_name=os.getenv("AWS_REGION_NAME"),
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        )
        ssm_client.put_parameter(
            Name=os.getenv("JWT_SECRET_SSM_PARAM_NAME"),
            Value=os.getenv("JWT_SECRET_SSM_PARAM_VALUE"),
            Type="SecureString",
        )
        yield


@pytest.fixture
def settings() -> Settings:
    return Settings()


@pytest.fixture
def dynamodb_resource(settings: Settings):
    with mock_aws():
        yield boto3.Session().resource(
            "dynamodb",
            region_name=os.getenv("AWS_REGION_NAME"),
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
        )


@pytest.fixture
def initialize_users_table(dynamodb_resource, user: User, users_table_name: str):
    users_table = dynamodb_resource.create_table(
        AttributeDefinitions=[
            {"AttributeName": "id", "AttributeType": "S"},
            {"AttributeName": "email", "AttributeType": "S"},
            {"AttributeName": "username", "AttributeType": "S"},
        ],
        TableName=users_table_name,
        KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
        GlobalSecondaryIndexes=[
            {
                "IndexName": "EmailIndex",
                "KeySchema": [
                    {"AttributeName": "email", "KeyType": "HASH"},
                ],
                "Projection": {
                    "ProjectionType": "ALL",
                },
            },
            {
                "IndexName": "UsernameIndex",
                "KeySchema": [
                    {"AttributeName": "username", "KeyType": "HASH"},
                ],
                "Projection": {
                    "ProjectionType": "ALL",
                },
            },
        ],
        ProvisionedThroughput={"ReadCapacityUnits": 1, "WriteCapacityUnits": 1},
    )
    users_table.put_item(Item=user.model_dump())


@pytest.fixture
def password() -> str:
    return "not_so_secure_password"


@pytest.fixture
def user_dict(password) -> dict[str, Any]:
    now = datetime.now(tz=UTC).isoformat()
    return {
        "display_name": "root",
        "email": "root@squarelabs.hu",
        "password": PasswordHasher().hash(password),
        "username": "root",
        "roles": ["root"],
        "created_at": now,
        "updated_at": now,
    }


@pytest.fixture
def user(user_dict: dict[str, Any]) -> User:
    return User(
        id=str(uuid.uuid4()),
        **user_dict,
    )


@pytest.fixture
def users_table(dynamodb_resource, initialize_users_table, users_table_name: str):
    return dynamodb_resource.Table(users_table_name)


@pytest.fixture
def users_table_name() -> str:
    return f"{os.getenv('STAGE')}-users"
