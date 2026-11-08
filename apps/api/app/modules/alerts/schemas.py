from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.shared.schemas import ApiModel


class AlertRead(ApiModel):
    id: UUID = Field(validation_alias="public_id")
    alert_type: str
    severity: str
    status: str
    title: str
    message: str
    entity_type: str | None
    entity_id: str | None
    extra: dict
    created_at: datetime
    read_at: datetime | None
    dismissed_at: datetime | None

    prospect_id: UUID | None = Field(validation_alias="prospect_public_id")
    prospect_name: str | None = Field(validation_alias="prospect_display_name")


class AlertFilters(BaseModel):
    status: str | None = Field(default=None, pattern=r"^(UNREAD|READ|DISMISSED)$")
    severity: str | None = Field(default=None, pattern=r"^(LOW|MEDIUM|HIGH|CRITICAL)$")
