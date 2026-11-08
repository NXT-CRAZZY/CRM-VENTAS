from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.modules.prospects.schemas import CatalogOptionTiny, ProspectContactRead, UserTiny
from app.shared.schemas import ApiModel


class InteractionRead(ApiModel):
    id: UUID = Field(validation_alias="public_id")
    occurred_at: datetime
    attempt_number: int
    notes: str | None
    next_action_desc: str | None
    next_action_at: datetime | None
    stage_before: str | None
    stage_after: str
    created_at: datetime
    updated_at: datetime

    user: UserTiny | None
    contact: ProspectContactRead | None
    channel: CatalogOptionTiny
    mode: CatalogOptionTiny | None
    result: CatalogOptionTiny
    interest_level: CatalogOptionTiny | None


class InteractionCreate(BaseModel):
    occurred_at: datetime
    channel_id: UUID
    mode_id: UUID | None = None
    result_id: UUID
    interest_level_id: UUID | None = None
    contact_id: UUID | None = None
    notes: str | None = Field(default=None, max_length=5000)
    next_action_desc: str | None = Field(default=None, max_length=200)
    next_action_at: datetime | None = None


class InteractionUpdate(BaseModel):
    occurred_at: datetime | None = None
    channel_id: UUID | None = None
    mode_id: UUID | None = None
    result_id: UUID | None = None
    interest_level_id: UUID | None = None
    contact_id: UUID | None = None
    notes: str | None = Field(default=None, max_length=5000)
    next_action_desc: str | None = Field(default=None, max_length=200)
    next_action_at: datetime | None = None


class InteractionListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(validation_alias="public_id")
    occurred_at: datetime
    attempt_number: int
    notes: str | None
    next_action_desc: str | None
    next_action_at: datetime | None
    stage_before: str | None
    stage_after: str
    created_at: datetime

    user: UserTiny | None
    contact: ProspectContactRead | None
    channel: CatalogOptionTiny
    mode: CatalogOptionTiny | None
    result: CatalogOptionTiny
    interest_level: CatalogOptionTiny | None
