from app.models.models import CamelModel
from app.models.user import User


class UsersPage(CamelModel):
    items: list[User]
    next_key: str | None = None
