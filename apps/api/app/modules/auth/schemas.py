from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.modules.rbac.schemas import RoleSummary
from app.modules.users.domain.password_policy import validate_password
from app.shared.schemas import ApiModel


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=200)


class SessionUser(ApiModel):
    id: UUID = Field(validation_alias="public_id")
    email: str
    full_name: str
    must_change_password: bool
    roles: list[RoleSummary]
    permissions: list[str] = Field(validation_alias="permission_codes")

    @field_validator("permissions", mode="before")
    @classmethod
    def _sorted(cls, v: object) -> object:
        return sorted(v) if isinstance(v, (set, list)) else v


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: SessionUser


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

    _pwd = field_validator("new_password")(validate_password)
