import os
from functools import cached_property

from aws_lambda_powertools.utilities import parameters
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str
    default_timezone: str
    aws_access_key_id: str
    aws_secret_access_key: str
    debug: bool = False
    stage: str
    rate_limiting: bool = False
    rate_limit_requests: int = 100
    rate_limit_duration_in_seconds: int = 60
    cors_allowed_origins: list[str] = ["*"]

    @cached_property
    def jwt_secret(self) -> str:
        return parameters.get_parameter(
            os.environ.get("JWT_SECRET_SSM_PARAM_NAME"), decrypt=True
        )
