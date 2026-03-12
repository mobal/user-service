from pydantic import EmailStr

from app.models.models import CamelModel


class UpdateUserRequest(CamelModel):
    display_name: str | None = None
    email: EmailStr | None = None
    username: str | None = None
