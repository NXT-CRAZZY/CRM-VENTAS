from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from app.core.deps import CurrentUser, DbSession, require
from app.modules.alerts.application.use_cases import AlertService
from app.modules.alerts.schemas import AlertFilters, AlertRead
from app.modules.rbac.domain.permissions import P
from app.shared.pagination import Page, PageParams, page_params

router = APIRouter(tags=["Alertas"], prefix="/alerts")


def _service(db: DbSession) -> AlertService:
    return AlertService(db)


Service = Annotated[AlertService, Depends(_service)]


@router.post("/generate", response_model=int, dependencies=[Depends(require(P.DASHBOARD_SALES))])
def generate_alerts(service: Service, user: CurrentUser) -> int:
    return service.generate_for_user(user)


@router.get("", response_model=Page[AlertRead])
def list_alerts(
    service: Service,
    user: CurrentUser,
    params: Annotated[PageParams, Depends(page_params)],
    status: str | None = None,
    severity: str | None = None,
) -> Page[AlertRead]:
    filters = AlertFilters(status=status, severity=severity)
    return service.list_alerts(filters, params, user)


@router.get("/unread-count", response_model=int)
def unread_count(service: Service, user: CurrentUser) -> int:
    return service.unread_count(user)


@router.patch("/{alert_id}/read", response_model=AlertRead)
def mark_read(alert_id: UUID, service: Service, user: CurrentUser) -> AlertRead:
    return AlertRead.model_validate(service.mark_read(alert_id, user))


@router.patch("/{alert_id}/dismiss", response_model=AlertRead)
def dismiss(alert_id: UUID, service: Service, user: CurrentUser) -> AlertRead:
    return AlertRead.model_validate(service.dismiss(alert_id, user))
