from pydantic import EmailStr, ValidationInfo, field_validator

from app.models.base import CamelCaseModel


class CreateUserRequest(CamelCaseModel):
    email: EmailStr
    username: str
    password: str
    confirm_password: str
    display_name: str | None = None

    @field_validator("confirm_password", mode="after")
    @staticmethod
    def passwords_match(cls, value: str, validation_info: ValidationInfo) -> str:
        if (
            "password" in validation_info.data
            and value != validation_info.data["password"]
        ):
            raise ValueError("Passwords do not match")
        return value


class UpdateUserRequest(CamelCaseModel):
    display_name: str | None = None
    email: EmailStr | None = None
    username: str | None = None


class ValidateUserRequest(CamelCaseModel):
    password: str
