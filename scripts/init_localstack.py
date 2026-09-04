"""Seed LocalStack with the AWS resources the user-service e2e suite needs.

Run against the compose ``app`` service after LocalStack is healthy::

    docker compose run --rm --no-deps app uv run python -m scripts.init_localstack

Creates the stage-prefixed DynamoDB tables (mirroring
``infrastructure/dynamodb.tf``), the shared JWT secret in SSM, and the ``root``
role row that the Postman collection's tokens reference.
"""

import os

import boto3

REGION = os.getenv("AWS_REGION_NAME", "eu-central-1")
STAGE = os.getenv("STAGE", "local")
# Dev-only secret, shared with the auth-service e2e suite (the Postman
# collection signs JWTs with the same value).
JWT_SECRET = "jwt-secret"

TABLES = {
    f"{STAGE}-users": {
        "AttributeDefinitions": [
            {"AttributeName": "id", "AttributeType": "S"},
            {"AttributeName": "email", "AttributeType": "S"},
            {"AttributeName": "username", "AttributeType": "S"},
        ],
        "KeySchema": [{"AttributeName": "id", "KeyType": "HASH"}],
        "GlobalSecondaryIndexes": [
            {
                "IndexName": "EmailIndex",
                "KeySchema": [{"AttributeName": "email", "KeyType": "HASH"}],
                "Projection": {"ProjectionType": "ALL"},
            },
            {
                "IndexName": "UsernameIndex",
                "KeySchema": [{"AttributeName": "username", "KeyType": "HASH"}],
                "Projection": {"ProjectionType": "ALL"},
            },
        ],
    },
    f"{STAGE}-roles": {
        "AttributeDefinitions": [
            {"AttributeName": "id", "AttributeType": "S"},
            {"AttributeName": "path", "AttributeType": "S"},
        ],
        "KeySchema": [{"AttributeName": "id", "KeyType": "HASH"}],
        "GlobalSecondaryIndexes": [
            {
                "IndexName": "PathIndex",
                "KeySchema": [{"AttributeName": "path", "KeyType": "HASH"}],
                "Projection": {"ProjectionType": "ALL"},
            }
        ],
    },
}


def _client(service: str):
    return boto3.client(
        service,
        region_name=REGION,
        endpoint_url=os.getenv("AWS_ENDPOINT_URL", "http://localstack:4566"),
    )


def create_tables() -> None:
    dynamodb = _client("dynamodb")

    for name, schema in TABLES.items():
        if name in dynamodb.list_tables().get("TableNames", []):
            print(f"table {name} already exists")
            continue
        dynamodb.create_table(TableName=name, BillingMode="PAY_PER_REQUEST", **schema)
        print(f"created table {name}")


def put_ssm_parameters() -> None:
    ssm = _client("ssm")

    parameters = {
        os.getenv(
            "JWT_SECRET_SSM_PARAM_NAME", f"/{STAGE}/secrets/jwt-secret"
        ): JWT_SECRET
    }

    for name, value in parameters.items():
        ssm.put_parameter(Name=name, Value=value, Type="SecureString", Overwrite=True)
        print(f"put parameter {name}")


def seed_root_role() -> None:
    """Insert the ``root`` role the Postman collection's admin token carries.

    The token's ``user.roles`` entry is resolved to permissions through the
    roles table, so the e2e suite exercises role-inheritance resolution (not
    just scope claims) on every authorized request.
    """
    dynamodb = boto3.resource(
        "dynamodb",
        region_name=REGION,
        endpoint_url=os.getenv("AWS_ENDPOINT_URL", "http://localstack:4566"),
    )
    table = dynamodb.Table(f"{STAGE}-roles")
    table.put_item(
        Item={
            "id": "root",
            "path": "root",
            "description": "Root role",
            "permissions": [
                "users:read",
                "users:write",
                "roles:read",
                "roles:write",
            ],
            "created_at": "2026-01-01T00:00:00+00:00",
        }
    )
    print(f"seeded role root in {STAGE}-roles")


if __name__ == "__main__":
    create_tables()
    put_ssm_parameters()
    seed_root_role()
    print("localstack seeded")
