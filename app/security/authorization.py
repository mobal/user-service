import functools

from aws_lambda_powertools import Logger
from fastapi import HTTPException, status

logger = Logger()


def pre_authorize(roles: list[str]):
    def decorator_wrapper(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            token = kwargs.get("token")

            user_roles = token.user.get("roles", [])

            if not any(role in user_roles for role in roles):
                logger.warning("User does not have required roles: %s", roles)
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions",
                )

            return func(*args, **kwargs)

        return wrapper

    return decorator_wrapper
