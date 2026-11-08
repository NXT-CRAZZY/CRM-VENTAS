from uuid import UUID

from app.core.errors import AppError, ConflictError, NotFoundError
from app.modules.audit.application.recorder import AuditRecorder, diff
from app.modules.catalogs.infrastructure.models import Catalog, CatalogOption
from app.modules.catalogs.repository import CatalogRepository
from app.modules.catalogs.schemas import (
    CatalogBundle,
    CatalogOptionCreate,
    CatalogOptionRead,
    CatalogOptionUpdate,
    CatalogRead,
)
from app.shared.text import slug_code

_FIELDS = ("code", "name", "description", "color", "legacy_code", "weight", "is_active")


def _snapshot(o: CatalogOption) -> dict:
    return {f: getattr(o, f) for f in _FIELDS}


class CatalogService:
    def __init__(self, repo: CatalogRepository, audit: AuditRecorder | None = None) -> None:
        self.repo = repo
        self.audit = audit

    def _catalog(self, code: str) -> Catalog:
        catalog = self.repo.get_catalog(code)
        if catalog is None:
            raise NotFoundError("El catálogo no existe.")
        return catalog

    def _option(self, option_id: UUID) -> CatalogOption:
        option = self.repo.get_option(option_id)
        if option is None:
            raise NotFoundError("La opción no existe.")
        return option

    def list_catalogs(self) -> list[CatalogRead]:
        out = []
        for catalog, count in self.repo.list_catalogs():
            item = CatalogRead.model_validate(catalog)
            item.option_count = count
            out.append(item)
        return out

    def list_options(self, code: str, include_inactive: bool) -> list[CatalogOptionRead]:
        catalog = self._catalog(code)
        return [CatalogOptionRead.model_validate(o) for o in self.repo.list_options(catalog.id, include_inactive)]

    def bundle(self, codes: list[str]) -> CatalogBundle:
        data = self.repo.options_for(codes)
        return CatalogBundle(catalogs={k: [CatalogOptionRead.model_validate(o) for o in v] for k, v in data.items()})

    def create_option(self, code: str, data: CatalogOptionCreate) -> CatalogOptionRead:
        catalog = self._catalog(code)
        option_code = data.code or slug_code(data.name)
        if not option_code:
            raise AppError("El nombre debe contener letras o números.", code="INVALID_NAME")
        if self.repo.get_option_by_code(catalog.id, option_code):
            raise ConflictError("Ya existe una opción con ese código en este catálogo.", code="OPTION_CODE_TAKEN")
        option = CatalogOption(
            catalog_id=catalog.id,
            code=option_code,
            name=data.name.strip(),
            description=data.description,
            color=data.color if catalog.uses_color else None,
            legacy_code=data.legacy_code,
            weight=data.weight if catalog.uses_weight else None,
            sort_order=self.repo.next_sort_order(catalog.id),
            is_active=True,
            is_system=False,
            extra={},
        )
        self.repo.add(option)
        if self.audit:
            self.audit.record(
                "catalog_option.created",
                f"catalog:{catalog.code}",
                option.public_id,
                label=option.name,
                after=_snapshot(option),
            )
        return CatalogOptionRead.model_validate(option)

    def update_option(self, option_id: UUID, data: CatalogOptionUpdate) -> CatalogOptionRead:
        option = self._option(option_id)
        before = _snapshot(option)
        changes = data.model_dump(exclude_unset=True)
        if option.is_system:
            if "code" in changes and changes["code"] != option.code:
                raise AppError("El código de una opción del sistema no se puede cambiar.", code="SYSTEM_OPTION")
            if changes.get("is_active") is False:
                raise AppError("Las opciones del sistema no se pueden desactivar.", code="SYSTEM_OPTION")
        new_code = changes.get("code")
        if new_code and new_code != option.code and self.repo.get_option_by_code(option.catalog_id, new_code):
            raise ConflictError("Ya existe una opción con ese código en este catálogo.", code="OPTION_CODE_TAKEN")
        if "name" in changes and changes["name"] is None:
            changes.pop("name")
        for field, value in changes.items():
            if field == "code" and not value:
                continue
            setattr(option, field, value.strip() if isinstance(value, str) and field == "name" else value)
        self.repo.add(option)
        if self.audit:
            b, a = diff(before, _snapshot(option))
            if a:
                self.audit.record(
                    "catalog_option.updated",
                    f"catalog:{option.catalog.code}",
                    option.public_id,
                    label=option.name,
                    before=b,
                    after=a,
                )
        return CatalogOptionRead.model_validate(option)

    def reorder(self, code: str, option_ids: list[UUID]) -> list[CatalogOptionRead]:
        catalog = self._catalog(code)
        options = {o.public_id: o for o in self.repo.list_options(catalog.id, include_inactive=True)}
        if set(option_ids) != set(options):
            raise AppError("La lista debe incluir todas las opciones del catálogo.", code="REORDER_MISMATCH")
        for index, oid in enumerate(option_ids):
            options[oid].sort_order = (index + 1) * 10
            self.repo.add(options[oid])
        return self.list_options(code, include_inactive=True)
