from typing import Annotated

from aws_lambda_powertools.logging import Logger
from fastapi import APIRouter, Depends, Query, Response, status

from app.jwt_bearer import JWTBearer, JWTToken
from app.models.request.filters import UserFilterParams
from app.models.request.register import RegistrationRequest
from app.models.request.update_user import UpdateUserRequest
from app.models.response.users_page import UsersPage
from app.security.authorization import pre_authorize
from app.services.user_service import UserService

logger = Logger()
router = APIRouter()
user_service = UserService()
jwt_bearer = JWTBearer()


@router.post("/users", status_code=status.HTTP_201_CREATED)
@pre_authorize(roles=["users:write"])
def register_user(
    body: RegistrationRequest, token: Annotated[JWTToken, Depends(jwt_bearer)]
):
    user_id = user_service.create_user(
        body.email, body.password, body.username, body.display_name
    )

    return Response(
        status_code=status.HTTP_201_CREATED,
        headers={"Location": f"/users/{user_id}"},
    )


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
@pre_authorize(roles=["users:write"])
def delete_user(user_id: str, token: Annotated[JWTToken, Depends(jwt_bearer)]):
    user_service.delete_user_by_id(user_id)


@router.get("/users/{user_id}")
@pre_authorize(roles=["users:read"])
def get_user_by_id(user_id: str, token: Annotated[JWTToken, Depends(jwt_bearer)]):
    user_service.get_user_by_id(user_id)


@router.get("/users")
@pre_authorize(roles=["users:read"])
def get_users(
    filters: Annotated[UserFilterParams, Query()],
    token: Annotated[JWTToken, Depends(jwt_bearer)],
) -> UsersPage:
    filter_values = filters.model_dump(
        exclude_none=True,
        exclude={"limit", "next_key"},
    )
    return user_service.get_users(
        filters=filter_values or None,
        limit=filters.limit,
        next_key=filters.next_key,
    )


@router.put("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
@pre_authorize(roles=["users:write"])
def update_user(
    user_id: str,
    body: UpdateUserRequest,
    token: Annotated[JWTToken, Depends(jwt_bearer)],
) -> None:
    user_service.update_user_by_id(user_id, body.model_dump(exclude_none=True))
