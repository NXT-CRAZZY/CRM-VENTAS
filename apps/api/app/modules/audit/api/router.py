from datetime import date, datetime, time, timedelta
from typing import Annotated, Any
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Query
from pydantic import Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.deps import DbSession, require
from app.modules.audit.infrastructure.models import AuditLog
from app.modules.rbac.domain.permissions import P
from app.modules.users.infrastructure.models import User
from app.shared.pagination import Page, PageParams, page_params, paginate
from app.shared.schemas import ApiModel

router = APIRouter(prefix="/audit-logs", tags=["Auditoría"])


class AuditUser(ApiModel):
    id: UUID = Field(validation_alias="public_id")
    full_name: str


class AuditLogRead(ApiModel):
    id: int
    action: str
    entity_type: str
    entity_id: str | None
    entity_label: str | None
    before: dict[str, Any] | None
    after: dict[str, Any] | None
    ip: str | None
    created_at: datetime
    user: AuditUser | None


def _local_bounds(day: date, end: bool) -> datetime:
    tz = ZoneInfo(get_settings().timezone)
    moment = datetime.combine(day + timedelta(days=1) if end else day, time.min, tzinfo=tz)
    return moment


def query_audit(
    db: Session,
    params: PageParams,
    *,
    action: str | None = None,
    entity_type: str | None = None,
    entity_id: str | None = None,
    user_id: UUID | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> Page[AuditLogRead]:
    stmt = select(AuditLog).order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
    if action:
        stmt = stmt.where(AuditLog.action.startswith(action))
    if entity_type:
        stmt = stmt.where(AuditLog.entity_type.startswith(entity_type))
    if entity_id:
        stmt = stmt.where(AuditLog.entity_id == entity_id)
    if user_id:
        stmt = stmt.where(AuditLog.user_id == select(User.id).where(User.public_id == user_id).scalar_subquery())
    if date_from:
        stmt = stmt.where(AuditLog.created_at >= _local_bounds(date_from, end=False))
    if date_to:
        stmt = stmt.where(AuditLog.created_at < _local_bounds(date_to, end=True))
    items, total = paginate(db, stmt, params)
    return Page[AuditLogRead](
        items=[AuditLogRead.model_validate(i) for i in items],
        total=total,
        page=params.page,
        page_size=params.page_size,
    )


@router.get("", response_model=Page[AuditLogRead], dependencies=[Depends(require(P.AUDIT_READ))])
def list_audit_logs(
    db: DbSession,
    params: Annotated[PageParams, Depends(page_params)],
    action: str | None = Query(None, description="Prefijo de acción, p.ej. 'user.'"),
    entity_type: str | None = None,
    entity_id: str | None = None,
    user_id: UUID | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> Page[AuditLogRead]:
    return query_audit(
        db,
        params,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        user_id=user_id,
        date_from=date_from,
        date_to=date_to,
    )
