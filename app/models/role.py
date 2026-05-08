from pydantic import Field

from app.models.base import CamelCaseModel


class Role(CamelCaseModel):
    id: str
    path: str
    description: str
    permissions: list[str] = Field(default_factory=list)
    created_at: str
    deleted_at: str | None = None
    updated_at: str | None = None
