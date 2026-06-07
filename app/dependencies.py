from fastapi import Request

from app.jwt_bearer import JWTBearer, JWTToken
from app.services.role_service import RoleService
from app.services.user_service import UserService


def get_jwt_bearer(request: Request) -> JWTToken:
    return JWTBearer().__call__(request)


def get_user_service() -> UserService:
    return UserService()


def get_role_service() -> RoleService:
    return RoleService()
