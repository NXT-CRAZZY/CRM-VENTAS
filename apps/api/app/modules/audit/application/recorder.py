from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Any, Protocol
from uuid import UUID

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser, DbSession, ReqCtx
from app.modules.audit.infrastructure.models import AuditLog


class AuditRecorder(Protocol):
    def record(
        self,
        action: str,
        entity_type: str,
        entity_id: str | UUID | None = None,
        *,
        label: str | None = None,
        before: dict[str, Any] | None = None,
        after: dict[str, Any] | None = None,
    ) -> None: ...


def _jsonable(data: dict[str, Any] | None) -> dict[str, Any] | None:
    if data is None:
        return None
    out: dict[str, Any] = {}
    for k, v in data.items():
        if isinstance(v, (UUID, Decimal)):
            v = str(v)
        elif isinstance(v, (datetime, date)):
            v = v.isoformat()
        elif isinstance(v, (set, tuple)):
            v = sorted(v)
        out[k] = v
    return out


def diff(before: dict[str, Any], after: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Devuelve solo los campos que cambiaron (auditoría compacta y legible)."""
    keys = [k for k in after if before.get(k) != after.get(k)]
    return {k: before.get(k) for k in keys}, {k: after.get(k) for k in keys}


class SqlAuditRecorder:
    """Escribe en la misma transacción del caso de uso: si la operación falla, no queda rastro falso."""

    def __init__(self, session: Session, actor_id: int | None, ip: str | None, user_agent: str | None):
        self._session = session
        self._actor_id = actor_id
        self._ip = ip
        self._ua = user_agent

    def record(
        self,
        action: str,
        entity_type: str,
        entity_id: str | UUID | None = None,
        *,
        label: str | None = None,
        before: dict[str, Any] | None = None,
        after: dict[str, Any] | None = None,
    ) -> None:
        self._session.add(
            AuditLog(
                user_id=self._actor_id,
                action=action,
                entity_type=entity_type,
                entity_id=str(entity_id) if entity_id else None,
                entity_label=label,
                before=_jsonable(before),
                after=_jsonable(after),
                ip=self._ip,
                user_agent=self._ua,
            )
        )


def get_audit(db: DbSession, user: CurrentUser, ctx: ReqCtx) -> AuditRecorder:
    return SqlAuditRecorder(db, user.id, ctx.ip, ctx.user_agent)


Audit = Annotated[AuditRecorder, Depends(get_audit)]
