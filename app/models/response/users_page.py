from app.models.base import CamelCaseModel
from app.models.response.user import UserResponse


class UsersPage(CamelCaseModel):
    items: list[UserResponse]
    next_key: str | None = None
