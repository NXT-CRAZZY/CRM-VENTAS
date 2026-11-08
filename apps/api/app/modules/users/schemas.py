from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.modules.rbac.schemas import RoleSummary
from app.modules.users.domain.password_policy import validate_password
from app.shared.schemas import ApiModel


class UserRead(ApiModel):
    id: UUID = Field(validation_alias="public_id")
    email: str
    full_name: str
    phone: str | None
    is_active: bool
    must_change_password: bool
    last_login_at: datetime | None
    deactivated_at: datetime | None
    created_at: datetime
    roles: list[RoleSummary]


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=3, max_length=150)
    phone: str | None = Field(default=None, max_length=30)
    password: str = Field(description="Contraseña temporal; el usuario deberá cambiarla al ingresar")
    role_ids: list[UUID] = Field(min_length=1)

    _pwd = field_validator("password")(validate_password)


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    full_name: str | None = Field(default=None, min_length=3, max_length=150)
    phone: str | None = Field(default=None, max_length=30)
    role_ids: list[UUID] | None = Field(default=None, min_length=1)


class PasswordReset(BaseModel):
    password: str

    _pwd = field_validator("password")(validate_password)


class UserFilters(BaseModel):
    q: str | None = None
    status: Literal["active", "inactive", "all"] = "active"
    role_id: UUID | None = None
