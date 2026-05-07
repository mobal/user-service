from pydantic import EmailStr

from app.models.base import CamelCaseModel


class User(CamelCaseModel):
    id: str
    display_name: str
    email: EmailStr
    password: str
    username: str
    roles: list[str] = []
    created_at: str
    deleted_at: str | None = None
    last_login_at: str | None = None
    updated_at: str | None = None
