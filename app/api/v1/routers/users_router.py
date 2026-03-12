from typing import Annotated

from aws_lambda_powertools.logging import Logger
from fastapi import APIRouter, Depends, Query, Response, status

from app import jwt_bearer
from app.models.request.filters import UserFilterParams
from app.models.request.register import RegistrationRequest
from app.models.request.update_user import UpdateUserRequest
from app.models.response.users_page import UsersPage
from app.security.authorization import pre_authorize
from app.services.user_service import UserService

logger = Logger()
router = APIRouter()
user_service = UserService()


@router.post(
    "/users", dependencies=[Depends(jwt_bearer)], status_code=status.HTTP_201_CREATED
)
@pre_authorize(roles=["root"])
def register_user(body: RegistrationRequest):
    user_id = user_service.create_user(
        body.email, body.password, body.username, body.display_name
    )

    return Response(
        status_code=status.HTTP_201_CREATED,
        headers={"Location": f"/users/{user_id}"},
    )


@router.delete(
    "/users/{user_id}",
    dependencies=[Depends(jwt_bearer)],
    status_code=status.HTTP_204_NO_CONTENT,
)
@pre_authorize(roles=["root"])
def delete_user(user_id: int):
    user_service.delete_user_by_id(user_id)


@router.get("/users/{user_id}", dependencies=[Depends(jwt_bearer)])
def get_user_by_id(user_id: int):
    user_service.get_user_by_id(user_id)


@router.get("/users", dependencies=[Depends(jwt_bearer)])
@pre_authorize(roles=["root"])
def get_users(filters: Annotated[UserFilterParams, Query()]) -> UsersPage:
    filter_values = filters.model_dump(
        exclude_none=True,
        exclude={"limit", "next_key"},
    )
    return user_service.get_users(
        filters=filter_values or None,
        limit=filters.limit,
        next_key=filters.next_key,
    )


@router.put(
    "/users/{user_id}",
    dependencies=[Depends(jwt_bearer)],
    status_code=status.HTTP_204_NO_CONTENT,
)
@pre_authorize(roles=["root"])
def update_user(user_id: int, body: UpdateUserRequest) -> None:
    user_service.update_user_by_id(user_id, body.model_dump(exclude_none=True))
