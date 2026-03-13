import functools

from aws_lambda_powertools import Logger
from fastapi import HTTPException, status

from app.models.jwt import JWTToken

logger = Logger()


def pre_authorize(roles: list[str]):
    def decorator_wrapper(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            token: JWTToken | None = kwargs.get("token")
            if token is None:
                logger.warning("Missing token during authorization check")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions",
                )

            permissions: set[str] = set()
            if token.scope:
                permissions.update(token.scope.split())

            user_roles = token.user.get("roles") if token.user else None
            if isinstance(user_roles, list):
                permissions.update(
                    role for role in user_roles if isinstance(role, str) and role
                )

            if not any(role in permissions for role in roles):
                logger.warning("User does not have required roles: %s", roles)
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions",
                )

            return func(*args, **kwargs)

        return wrapper

    return decorator_wrapper
