from pydantic import EmailStr, Field, ValidationInfo, field_validator

from app.models.base import RequestModel


class CreateUserRequest(RequestModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_-]+$")
    password: str = Field(min_length=8, max_length=128)
    confirm_password: str
    display_name: str | None = Field(default=None, min_length=1, max_length=100)

    @field_validator("confirm_password", mode="after")
    @staticmethod
    def passwords_match(cls, value: str, validation_info: ValidationInfo) -> str:
        if (
            "password" in validation_info.data
            and value != validation_info.data["password"]
        ):
            raise ValueError("Passwords do not match")
        return value


class UpdateUserRequest(RequestModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=100)
    email: EmailStr | None = None
    username: str | None = Field(default=None, min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_-]+$")


class ValidateUserRequest(RequestModel):
    password: str
