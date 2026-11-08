from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from app.shared.schemas import ApiModel
from app.shared.text import HEX_COLOR


class CatalogRead(ApiModel):
    id: UUID = Field(validation_alias="public_id")
    code: str
    name: str
    description: str | None
    uses_color: bool
    uses_weight: bool
    option_count: int = 0


class CatalogOptionRead(ApiModel):
    id: UUID = Field(validation_alias="public_id")
    code: str
    name: str
    description: str | None
    color: str | None
    sort_order: int
    is_active: bool
    legacy_code: str | None
    weight: Decimal | None
    is_system: bool


class CatalogOptionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    code: str | None = Field(default=None, max_length=40, pattern=r"^[A-Z0-9_]+$")
    description: str | None = Field(default=None, max_length=500)
    color: str | None = Field(default=None, pattern=HEX_COLOR)
    legacy_code: str | None = Field(default=None, max_length=20)
    weight: Decimal | None = Field(default=None, ge=-1000, le=1000)


class CatalogOptionUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    code: str | None = Field(default=None, max_length=40, pattern=r"^[A-Z0-9_]+$")
    description: str | None = Field(default=None, max_length=500)
    color: str | None = Field(default=None, pattern=HEX_COLOR)
    legacy_code: str | None = Field(default=None, max_length=20)
    weight: Decimal | None = Field(default=None, ge=-1000, le=1000)
    is_active: bool | None = None


class ReorderRequest(BaseModel):
    option_ids: list[UUID] = Field(min_length=1)


class CatalogBundle(BaseModel):
    """Opciones activas de varios catálogos en una sola llamada (para formularios)."""

    catalogs: dict[str, list[CatalogOptionRead]]
