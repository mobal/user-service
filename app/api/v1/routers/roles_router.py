from typing import Annotated

from aws_lambda_powertools.logging import Logger
from fastapi import APIRouter, Depends, Response, status

from app.exceptions import NotFoundException
from app.jwt_bearer import JWTBearer, JWTToken
from app.models.request.role_requests import CreateRoleRequest, UpdateRoleRequest
from app.models.role import Role
from app.security.authorization import pre_authorize
from app.services.role_service import RoleService

logger = Logger()
router = APIRouter()
role_service = RoleService()
jwt_bearer = JWTBearer()


@router.post("/roles", status_code=status.HTTP_201_CREATED)
@pre_authorize(roles=["roles:write"])
def create_role(
    body: CreateRoleRequest, token: Annotated[JWTToken, Depends(jwt_bearer)]
):
    role = role_service.create_role(body.model_dump(exclude_none=True))

    return Response(
        status_code=status.HTTP_201_CREATED,
        headers={"Location": f"/roles/{role['id']}"},
    )


@router.delete("/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
@pre_authorize(roles=["roles:write"])
def delete_role(role_id: str, token: Annotated[JWTToken, Depends(jwt_bearer)]):
    role_service.delete_role(role_id)


@router.get("/roles/{role_id}")
@pre_authorize(roles=["roles:read"])
def get_role_by_id(role_id: str, token: Annotated[JWTToken, Depends(jwt_bearer)]):
    role = role_service.get_role_by_id(role_id)
    if not role:
        raise NotFoundException(f"Role with id {role_id} not found")

    return Role(**role.model_dump())


@router.get("/roles/name/{role_name}")
@pre_authorize(roles=["roles:read"])
def get_role_by_name(role_name: str, token: Annotated[JWTToken, Depends(jwt_bearer)]):
    role = role_service.get_role_by_name(role_name)
    if not role:
        raise NotFoundException(f"Role with name {role_name} not found")

    return Role(**role.model_dump())


@router.put("/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
@pre_authorize(roles=["roles:write"])
def update_role(
    role_id: str,
    body: UpdateRoleRequest,
    token: Annotated[JWTToken, Depends(jwt_bearer)],
) -> None:
    role_service.update_role(role_id, body.model_dump(exclude_none=True))
