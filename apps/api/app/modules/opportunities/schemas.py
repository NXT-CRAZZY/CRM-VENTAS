from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from app.modules.prospects.schemas import CatalogOptionTiny, UserTiny
from app.shared.schemas import ApiModel


class OpportunityProspectTiny(ApiModel):
    id: UUID = Field(validation_alias="public_id")
    display_name: str
    status: str


class OpportunityRead(ApiModel):
    id: UUID = Field(validation_alias="public_id")
    title: str
    description: str | None
    estimated_amount: Decimal | None
    probability: int | None
    expected_close_date: date | None
    actual_close_date: date | None
    created_at: datetime
    updated_at: datetime

    stage: CatalogOptionTiny
    type: CatalogOptionTiny | None
    loss_reason: CatalogOptionTiny | None
    owner: UserTiny | None
    prospect: OpportunityProspectTiny


class OpportunityCreate(BaseModel):
    prospect_id: UUID
    title: str = Field(min_length=2, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    stage_id: UUID
    type_id: UUID | None = None
    loss_reason_id: UUID | None = None
    owner_id: UUID | None = None
    estimated_amount: float | None = Field(default=None, ge=0)
    probability: int | None = Field(default=None, ge=0, le=100)
    expected_close_date: date | None = None


class OpportunityUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    stage_id: UUID | None = None
    type_id: UUID | None = None
    loss_reason_id: UUID | None = None
    owner_id: UUID | None = None
    estimated_amount: float | None = Field(default=None, ge=0)
    probability: int | None = Field(default=None, ge=0, le=100)
    expected_close_date: date | None = None
    actual_close_date: date | None = None


class OpportunityFilters(BaseModel):
    stage_id: UUID | None = None
    owner_id: UUID | None = None
    type_id: UUID | None = None
    expected_close_before: date | None = None
    expected_close_after: date | None = None
