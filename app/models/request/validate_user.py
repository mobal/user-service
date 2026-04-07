from app.models.models import CamelModel


class ValiateUserRequest(CamelModel):
    password: str
