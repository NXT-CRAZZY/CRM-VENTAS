from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.modules.prospects.schemas import CatalogOptionTiny, ProspectContactRead, UserTiny
from app.modules.tasks.schemas import TaskRead
from app.shared.schemas import ApiModel


class InteractionOpportunityTiny(ApiModel):
    id: UUID = Field(validation_alias="public_id")
    title: str
    stage: CatalogOptionTiny


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
    follow_up_task: TaskRead | None = None
    opportunity: InteractionOpportunityTiny | None = None
    # created | moved | closed: solo se informa en la respuesta de crear/editar (para avisar al usuario).
    opportunity_action: str | None = None


class FollowUpTask(BaseModel):
    """Próxima acción de la interacción: los mismos campos que una tarea."""

    title: str = Field(min_length=2, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    assignee_id: UUID | None = None
    type_id: UUID | None = None
    priority_id: UUID | None = None
    due_at: datetime
    remind_at: datetime | None = None


class InteractionNewOpportunity(BaseModel):
    """Datos para crear una oportunidad nueva desde la interacción."""

    title: str = Field(min_length=2, max_length=200)
    type_id: UUID


class InteractionCreate(BaseModel):
    occurred_at: datetime
    channel_id: UUID
    result_id: UUID
    interest_level_id: UUID | None = None
    contact_id: UUID | None = None
    notes: str | None = Field(default=None, max_length=5000)
    follow_up_task: FollowUpTask | None = None
    # Oportunidad abierta a la que aplica el resultado, o datos para crear una nueva.
    opportunity_id: UUID | None = None
    new_opportunity: InteractionNewOpportunity | None = None


class InteractionUpdate(BaseModel):
    occurred_at: datetime | None = None
    channel_id: UUID | None = None
    result_id: UUID | None = None
    interest_level_id: UUID | None = None
    contact_id: UUID | None = None
    notes: str | None = Field(default=None, max_length=5000)
    follow_up_task: FollowUpTask | None = None
    remove_follow_up_task: bool = False
    opportunity_id: UUID | None = None
    new_opportunity: InteractionNewOpportunity | None = None


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
