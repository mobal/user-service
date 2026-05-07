from app.models.base import CamelCaseModel


class Role(CamelCaseModel):
    id: str
    role_name: str
    path: str
    permissions: list[str]
    created_at: str
    deleted_at: str | None = None
    updated_at: str | None = None
