from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from app.modules.products.domain.enums import BillingPeriod, ProductKind
from app.shared.schemas import ApiModel


class CategoryRead(ApiModel):
    id: UUID = Field(validation_alias="public_id")
    code: str
    name: str
    product_line: str
    sort_order: int
    is_active: bool
    product_count: int = 0


class CategoryCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    product_line: str = Field(min_length=2, max_length=40)


class CategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    product_line: str | None = Field(default=None, min_length=2, max_length=40)
    is_active: bool | None = None


class CategorySummary(ApiModel):
    id: UUID = Field(validation_alias="public_id")
    name: str
    product_line: str


class ProductRead(ApiModel):
    id: UUID = Field(validation_alias="public_id")
    code: str
    name: str
    description: str | None
    category: CategorySummary
    kind: ProductKind
    billing_period: BillingPeriod
    list_price: Decimal
    is_active: bool
    legacy_code: str | None


class ProductCreate(BaseModel):
    code: str = Field(min_length=2, max_length=30, pattern=r"^[A-Za-z0-9_\-]+$")
    name: str = Field(min_length=2, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    category_id: UUID
    kind: ProductKind
    billing_period: BillingPeriod
    list_price: Decimal = Field(ge=0, max_digits=14, decimal_places=2, description="Precio final en soles")
    legacy_code: str | None = Field(default=None, max_length=20)


class ProductUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=2, max_length=30, pattern=r"^[A-Za-z0-9_\-]+$")
    name: str | None = Field(default=None, min_length=2, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    category_id: UUID | None = None
    kind: ProductKind | None = None
    billing_period: BillingPeriod | None = None
    list_price: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    legacy_code: str | None = Field(default=None, max_length=20)
    is_active: bool | None = None


class ProductFilters(BaseModel):
    q: str | None = None
    category_id: UUID | None = None
    product_line: str | None = None
    status: str = "active"  # active | inactive | all
