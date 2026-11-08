from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from app.core.deps import CurrentUser, DbSession, require
from app.modules.audit.application.recorder import Audit
from app.modules.opportunities.application.use_cases import OpportunityService
from app.modules.opportunities.repository import SqlOpportunityRepository
from app.modules.opportunities.schemas import (
    OpportunityCreate,
    OpportunityRead,
    OpportunityUpdate,
)
from app.modules.rbac.domain.permissions import P
from app.shared.pagination import Page, PageParams, page_params

router = APIRouter(tags=["Oportunidades"])


def _service(db: DbSession, audit: Audit) -> OpportunityService:
    return OpportunityService(SqlOpportunityRepository(db), audit)


Service = Annotated[OpportunityService, Depends(_service)]


@router.get("/opportunities", response_model=Page[OpportunityRead])
def list_opportunities(
    service: Service,
    user: CurrentUser,
    params: Annotated[PageParams, Depends(page_params)],
    stage_id: UUID | None = None,
    owner_id: UUID | None = None,
    type_id: UUID | None = None,
    prospect_id: UUID | None = None,
    expected_close_before: str | None = None,
    expected_close_after: str | None = None,
) -> Page[OpportunityRead]:
    filters = {
        "stage_id": stage_id,
        "owner_id": owner_id,
        "type_id": type_id,
        "prospect_id": prospect_id,
        "expected_close_before": expected_close_before,
        "expected_close_after": expected_close_after,
    }
    return service.list_opportunities(
        {k: v for k, v in filters.items() if v is not None}, params, user
    )


@router.post(
    "/opportunities",
    response_model=OpportunityRead,
    status_code=201,
    dependencies=[Depends(require(P.OPPORTUNITIES_MANAGE))],
)
def create_opportunity(data: OpportunityCreate, service: Service, user: CurrentUser) -> OpportunityRead:
    return service.create_opportunity(data, user)


@router.patch("/opportunities/{opportunity_id}", response_model=OpportunityRead)
def update_opportunity(
    opportunity_id: UUID, data: OpportunityUpdate, service: Service, user: CurrentUser
) -> OpportunityRead:
    return service.update_opportunity(opportunity_id, data, user)


@router.delete("/opportunities/{opportunity_id}", status_code=204)
def delete_opportunity(opportunity_id: UUID, service: Service, user: CurrentUser) -> None:
    service.delete_opportunity(opportunity_id, user)
