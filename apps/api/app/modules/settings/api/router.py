from typing import Any

from fastapi import APIRouter, Body, Depends

from app.core.deps import CurrentUser, DbSession, require
from app.modules.audit.application.recorder import Audit
from app.modules.rbac.domain.permissions import P
from app.modules.settings.application.use_cases import SettingGroup, SettingsService

router = APIRouter(prefix="/settings", tags=["Configuración"])


@router.get("", response_model=list[SettingGroup], dependencies=[Depends(require(P.SETTINGS_READ))])
def list_settings(db: DbSession) -> list[SettingGroup]:
    return SettingsService(db).list()


@router.put("/{key}", response_model=SettingGroup, dependencies=[Depends(require(P.SETTINGS_MANAGE))])
def update_setting(
    key: str, db: DbSession, audit: Audit, user: CurrentUser, payload: dict[str, Any] = Body(...)
) -> SettingGroup:
    return SettingsService(db, audit, user.id).update(key, payload)
