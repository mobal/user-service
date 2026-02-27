from pydantic import EmailStr

from app.models.models import CamelModel


class User(CamelModel):
    id: int
    display_name: str
    email: EmailStr
    password: str
    username: str
    roles: list[str] = []
    created_at: str
    deleted_at: str | None = None
    updated_at: str | None = None
