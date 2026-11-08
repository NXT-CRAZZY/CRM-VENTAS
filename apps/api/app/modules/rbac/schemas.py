from collections.abc import Iterable
from typing import Any, cast
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.shared.schemas import ApiModel


class PermissionRead(ApiModel):
    code: str
    module: str
    name: str


class PermissionGroup(BaseModel):
    module: str
    permissions: list[PermissionRead]


class RoleRead(ApiModel):
    id: UUID = Field(validation_alias="public_id")
    code: str
    name: str
    description: str | None
    is_system: bool
    permissions: list[str]
    user_count: int = 0

    @field_validator("permissions", mode="before")
    @classmethod
    def _codes(cls, v: object) -> list[str]:
        return [getattr(p, "code", p) for p in cast(Iterable[Any], v)]


class RoleSummary(ApiModel):
    id: UUID = Field(validation_alias="public_id")
    code: str
    name: str


class RoleCreate(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    description: str | None = Field(default=None, max_length=500)
    permissions: list[str] = Field(default_factory=list)


class RoleUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=80)
    description: str | None = Field(default=None, max_length=500)
    permissions: list[str] | None = None
