from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.core.deps import CurrentUser, DbSession, require
from app.modules.audit.application.recorder import Audit
from app.modules.prospects.application.use_cases import ProspectService
from app.modules.prospects.repository import SqlProspectRepository
from app.modules.prospects.schemas import (
    AssignRequest,
    BulkAssignRequest,
    DuplicateCheckRequest,
    DuplicateCheckResult,
    ProspectAssignmentRead,
    ProspectCreate,
    ProspectFilters,
    ProspectRead,
    ProspectStatusHistoryRead,
    ProspectUpdate,
    StatusChangeRequest,
    TagCreate,
    TagRead,
)
from app.modules.rbac.domain.permissions import P
from app.modules.users.infrastructure.models import User
from app.shared.pagination import Page, PageParams, page_params

router = APIRouter(tags=["Prospectos"])

CanReadOwn = Depends(require(P.PROSPECTS_READ_OWN))
CanReadAll = Depends(require(P.PROSPECTS_READ_ALL))
CanCreate = Depends(require(P.PROSPECTS_CREATE))
CanUpdateOwn = Depends(require(P.PROSPECTS_UPDATE_OWN))
CanUpdateAll = Depends(require(P.PROSPECTS_UPDATE_ALL))
CanAssign = Depends(require(P.PROSPECTS_ASSIGN))
CanDelete = Depends(require(P.PROSPECTS_DELETE))


def _service(db: DbSession, audit: Audit, user: CurrentUser) -> ProspectService:
    return ProspectService(SqlProspectRepository(db), audit)


Service = Annotated[ProspectService, Depends(_service)]


def _read_scope(user: CurrentUser) -> None:
    if P.PROSPECTS_READ_ALL not in user.permission_codes and P.PROSPECTS_READ_OWN not in user.permission_codes:
        raise PermissionError("No tienes permiso para ver prospectos.")


@router.get("/prospects", response_model=Page[ProspectRead])
def list_prospects(
    service: Service,
    user: CurrentUser,
    params: Annotated[PageParams, Depends(page_params)],
    q: str | None = Query(None, description="Búsqueda por nombre, correo, teléfono, documento o código"),
    person_type: str | None = None,
    status: str | None = None,
    relationship_type: str | None = None,
    owner_id: UUID | None = None,
    interest_level_id: UUID | None = None,
    priority_id: UUID | None = None,
    source_id: UUID | None = None,
) -> Page[ProspectRead]:
    _read_scope(user)
    filters = ProspectFilters(
        q=q,
        person_type=person_type,
        status=status,
        relationship_type=relationship_type,
        owner_id=owner_id,
        interest_level_id=interest_level_id,
        priority_id=priority_id,
        source_id=source_id,
    )
    return service.list_prospects(filters, params, user)


@router.post("/prospects", response_model=ProspectRead, status_code=status.HTTP_201_CREATED)
def create_prospect(data: ProspectCreate, service: Service, user: CurrentUser) -> ProspectRead:
    return service.create_prospect(data, user)


@router.get("/prospects/{prospect_id}", response_model=ProspectRead)
def get_prospect(prospect_id: UUID, service: Service, user: CurrentUser) -> ProspectRead:
    return service.get_prospect(prospect_id, user)


@router.get("/prospects/{prospect_id}/assignments", response_model=list[ProspectAssignmentRead])
def get_prospect_assignments(prospect_id: UUID, service: Service, user: CurrentUser) -> list[ProspectAssignmentRead]:
    return service.get_prospect_assignments(prospect_id, user)


@router.get("/prospects/{prospect_id}/status-history", response_model=list[ProspectStatusHistoryRead])
def get_prospect_status_history(prospect_id: UUID, service: Service, user: CurrentUser) -> list[ProspectStatusHistoryRead]:
    return service.get_prospect_status_history(prospect_id, user)


@router.patch("/prospects/{prospect_id}", response_model=ProspectRead)
def update_prospect(prospect_id: UUID, data: ProspectUpdate, service: Service, user: CurrentUser) -> ProspectRead:
    return service.update_prospect(prospect_id, data, user)


@router.delete("/prospects/{prospect_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_prospect(prospect_id: UUID, service: Service, user: CurrentUser) -> None:
    service.delete_prospect(prospect_id, user)


@router.post("/prospects/duplicate-check", response_model=DuplicateCheckResult)
def duplicate_check(
    request: DuplicateCheckRequest,
    service: Service,
    exclude: UUID | None = Query(None, description="Excluir este prospecto de la búsqueda (útil al editar)"),
) -> DuplicateCheckResult:
    return service.check_duplicates(request, exclude)


@router.post("/prospects/{prospect_id}/assign", response_model=ProspectRead)
def assign_prospect(prospect_id: UUID, request: AssignRequest, service: Service, user: CurrentUser) -> ProspectRead:
    return service.assign_prospect(prospect_id, request, user)


@router.post("/prospects/bulk-assign")
def bulk_assign(request: BulkAssignRequest, service: Service, user: CurrentUser) -> dict:
    return service.bulk_assign(request, user)


@router.post("/prospects/{prospect_id}/status", response_model=ProspectRead)
def change_status(
    prospect_id: UUID, request: StatusChangeRequest, service: Service, user: CurrentUser
) -> ProspectRead:
    return service.change_status(prospect_id, request, user)


@router.get("/tags", response_model=list[TagRead], dependencies=[Depends(require(P.PROSPECTS_READ_OWN))])
def list_tags(service: Service) -> list[TagRead]:
    return service.list_tags()


@router.post("/tags", response_model=TagRead, status_code=status.HTTP_201_CREATED, dependencies=[CanUpdateAll])
def create_tag(data: TagCreate, service: Service) -> TagRead:
    return service.create_tag(data)
