from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.modules.prospects.schemas import CatalogOptionTiny, ProspectContactRead, UserTiny
from app.shared.schemas import ApiModel


class TaskProspectTiny(ApiModel):
    id: UUID = Field(validation_alias="public_id")
    display_name: str
    status: str


class TaskRead(ApiModel):
    id: UUID = Field(validation_alias="public_id")
    title: str
    description: str | None
    due_at: datetime | None
    remind_at: datetime | None
    status: str
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    assignee: UserTiny | None
    type: CatalogOptionTiny | None
    priority: CatalogOptionTiny | None
    prospect: TaskProspectTiny | None = None


class TaskCreate(BaseModel):
    prospect_id: UUID
    title: str = Field(min_length=2, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    assignee_id: UUID | None = None
    type_id: UUID | None = None
    priority_id: UUID | None = None
    due_at: datetime | None = None
    remind_at: datetime | None = None


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    assignee_id: UUID | None = None
    type_id: UUID | None = None
    priority_id: UUID | None = None
    due_at: datetime | None = None
    remind_at: datetime | None = None
    status: str | None = None


class TaskListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(validation_alias="public_id")
    prospect_id: UUID
    title: str
    description: str | None
    due_at: datetime | None
    status: str
    completed_at: datetime | None
    created_at: datetime

    assignee: UserTiny | None
    type: CatalogOptionTiny | None
    priority: CatalogOptionTiny | None
    prospect: TaskProspectTiny | None


class TaskStatusChange(BaseModel):
    status: str = Field(pattern=r"^(PENDING|DONE|CANCELLED)$")


class TaskFilters(BaseModel):
    status: str | None = None
    assignee_id: UUID | None = None
    due_before: datetime | None = None
    due_after: datetime | None = None
