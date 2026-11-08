from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.modules.opportunities.schemas import OpportunityProspectTiny
from app.modules.prospects.schemas import UserTiny
from app.shared.schemas import ApiModel


class ProductTiny(ApiModel):
    id: UUID = Field(validation_alias="public_id")
    code: str
    name: str
    list_price: Decimal


class QuoteItemRead(ApiModel):
    id: UUID = Field(validation_alias="public_id")
    description: str
    quantity: int
    unit_price: Decimal
    total: Decimal
    product: ProductTiny | None


class QuoteItemCreate(BaseModel):
    product_id: UUID | None = None
    description: str = Field(min_length=1, max_length=255)
    quantity: int = Field(ge=1)
    unit_price: float = Field(ge=0)


class QuoteItemUpdate(BaseModel):
    product_id: UUID | None = None
    description: str | None = Field(default=None, min_length=1, max_length=255)
    quantity: int | None = Field(default=None, ge=1)
    unit_price: float | None = Field(default=None, ge=0)


class QuoteRead(ApiModel):
    id: UUID = Field(validation_alias="public_id")
    status: str
    issue_date: date
    expiration_date: date | None
    subtotal: Decimal
    tax: Decimal
    total: Decimal
    notes: str | None
    created_at: datetime
    updated_at: datetime

    prospect: OpportunityProspectTiny
    opportunity: "QuoteOpportunityTiny | None" = None
    items: list[QuoteItemRead]


class QuoteOpportunityTiny(ApiModel):
    id: UUID = Field(validation_alias="public_id")
    title: str


class QuoteCreate(BaseModel):
    prospect_id: UUID
    opportunity_id: UUID | None = None
    issue_date: date
    expiration_date: date | None = None
    notes: str | None = Field(default=None, max_length=5000)
    items: list[QuoteItemCreate] = Field(min_length=1)


class QuoteUpdate(BaseModel):
    opportunity_id: UUID | None = None
    issue_date: date | None = None
    expiration_date: date | None = None
    notes: str | None = Field(default=None, max_length=5000)
    items: list[QuoteItemCreate] | None = None


class QuoteStatusChange(BaseModel):
    status: str = Field(pattern=r"^(DRAFT|SENT|ACCEPTED|REJECTED)$")


class QuoteFilters(BaseModel):
    status: str | None = None
    prospect_id: UUID | None = None
    opportunity_id: UUID | None = None
