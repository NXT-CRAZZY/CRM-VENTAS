from typing import Any

from pydantic import BaseModel, ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError, NotFoundError
from app.modules.audit.application.recorder import AuditRecorder, diff
from app.modules.settings.domain.registry import SETTINGS_REGISTRY
from app.modules.settings.infrastructure.models import AppSetting


class SettingGroup(BaseModel):
    key: str
    label: str
    value: dict[str, Any]
    fields: dict[str, Any]


class SettingsService:
    """Lectura/escritura de configuración. Los valores faltantes se completan con los defaults."""

    def __init__(self, session: Session, audit: AuditRecorder | None = None, actor_id: int | None = None):
        self.s = session
        self.audit = audit
        self.actor_id = actor_id

    def _stored(self) -> dict[str, AppSetting]:
        return {row.key: row for row in self.s.scalars(select(AppSetting))}

    def get(self, key: str) -> BaseModel:
        if key not in SETTINGS_REGISTRY:
            raise NotFoundError("La configuración no existe.")
        model = SETTINGS_REGISTRY[key][1]
        row = self.s.get(AppSetting, key)
        return model.model_validate(row.value if row else {})

    def list(self) -> list[SettingGroup]:
        stored = self._stored()
        groups = []
        for key, (label, model) in SETTINGS_REGISTRY.items():
            value = model.model_validate(stored[key].value if key in stored else {})
            schema = model.model_json_schema()
            groups.append(
                SettingGroup(key=key, label=label, value=value.model_dump(mode="json"), fields=schema["properties"])
            )
        return groups

    def update(self, key: str, payload: dict[str, Any]) -> SettingGroup:
        if key not in SETTINGS_REGISTRY:
            raise NotFoundError("La configuración no existe.")
        label, model = SETTINGS_REGISTRY[key]
        current = self.get(key).model_dump(mode="json")
        try:
            new_value = model.model_validate({**current, **payload}).model_dump(mode="json")
        except ValidationError as exc:
            raise AppError(
                "Revisa los valores de configuración.",
                code="VALIDATION_ERROR",
                details=[{"field": ".".join(map(str, e["loc"])), "message": e["msg"]} for e in exc.errors()],
            ) from exc
        row = self.s.get(AppSetting, key)
        if row is None:
            row = AppSetting(key=key, value=new_value)
        row.value = new_value
        row.updated_by_id = self.actor_id
        self.s.add(row)
        self.s.flush()
        if self.audit:
            b, a = diff(current, new_value)
            if a:
                self.audit.record("settings.updated", "settings", key, label=label, before=b, after=a)
        return SettingGroup(key=key, label=label, value=new_value, fields=model.model_json_schema()["properties"])
