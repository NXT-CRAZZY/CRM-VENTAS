from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from app.core.deps import CurrentUser, DbSession, require
from app.modules.audit.application.recorder import Audit
from app.modules.interactions.application.use_cases import InteractionService
from app.modules.interactions.repository import SqlInteractionRepository
from app.modules.interactions.schemas import InteractionCreate, InteractionRead, InteractionUpdate
from app.modules.opportunities.application.use_cases import OpportunityService
from app.modules.opportunities.repository import SqlOpportunityRepository
from app.modules.rbac.domain.permissions import P
from app.modules.tasks.application.use_cases import TaskService
from app.modules.tasks.repository import SqlTaskRepository
from app.shared.pagination import Page, PageParams

router = APIRouter(tags=["Interacciones"])


def _service(db: DbSession, audit: Audit) -> InteractionService:
    return InteractionService(
        SqlInteractionRepository(db),
        audit,
        TaskService(SqlTaskRepository(db), audit),
        OpportunityService(SqlOpportunityRepository(db), audit),
    )


Service = Annotated[InteractionService, Depends(_service)]


@router.get("/prospects/{prospect_id}/interactions", response_model=Page[InteractionRead])
def list_interactions(
    prospect_id: UUID,
    service: Service,
    user: CurrentUser,
    params: Annotated[PageParams, Depends()],
) -> Page[InteractionRead]:
    return service.list_interactions(prospect_id, params, user)


@router.post(
    "/prospects/{prospect_id}/interactions",
    response_model=InteractionRead,
    status_code=201,
    dependencies=[Depends(require(P.INTERACTIONS_CREATE))],
)
def create_interaction(
    prospect_id: UUID,
    data: InteractionCreate,
    service: Service,
    user: CurrentUser,
) -> InteractionRead:
    return service.create_interaction(prospect_id, data, user)


@router.patch("/prospects/{prospect_id}/interactions/{interaction_id}", response_model=InteractionRead)
def update_interaction(
    prospect_id: UUID,
    interaction_id: UUID,
    data: InteractionUpdate,
    service: Service,
    user: CurrentUser,
) -> InteractionRead:
    return service.update_interaction(prospect_id, interaction_id, data, user)


@router.delete("/prospects/{prospect_id}/interactions/{interaction_id}", status_code=204)
def delete_interaction(
    prospect_id: UUID,
    interaction_id: UUID,
    service: Service,
    user: CurrentUser,
) -> None:
    service.delete_interaction(prospect_id, interaction_id, user)
