from app.models.models import CamelModel
from app.models.response.user import UserResponse


class UsersPage(CamelModel):
    items: list[UserResponse]
    next_key: str | None = None
