from aws_lambda_powertools.logging import Logger
from fastapi import APIRouter, Depends, Response, status

from app import jwt_bearer
from app.models.request.register import RegistrationRequest
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
def get_users() -> list:
    return user_service.get_users()


@router.put(
    "/users/{user_id}",
    dependencies=[Depends(jwt_bearer)],
    status_code=status.HTTP_204_NO_CONTENT,
)
@pre_authorize(roles=["root"])
def update_user(user_id: int) -> None:
    # Update user logic to be implemented
    pass
