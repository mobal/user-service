from app.models.models import CamelModel


class UserResponse(CamelModel):
    id: str
    display_name: str
    email: str
    username: str
    roles: list[str] = []
    created_at: str
    updated_at: str | None = None
