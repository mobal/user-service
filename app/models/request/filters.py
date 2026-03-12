from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserFilterParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str | None = None
    email: EmailStr | None = None
    display_name: str | None = None
    limit: int = Field(default=50, ge=1, le=200)
    next_key: str | None = None
