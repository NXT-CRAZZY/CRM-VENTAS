from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.core.deps import CurrentUser, DbSession, require
from app.modules.audit.application.recorder import Audit
from app.modules.catalogs.application.use_cases import CatalogService
from app.modules.catalogs.repository import SqlCatalogRepository
from app.modules.catalogs.schemas import (
    CatalogBundle,
    CatalogOptionCreate,
    CatalogOptionRead,
    CatalogOptionUpdate,
    CatalogRead,
    ReorderRequest,
)
from app.modules.rbac.domain.permissions import P

router = APIRouter(tags=["Catálogos"])
CanManage = Depends(require(P.CATALOGS_MANAGE))


def _service(db: DbSession, audit: Audit) -> CatalogService:
    return CatalogService(SqlCatalogRepository(db), audit)


Service = Annotated[CatalogService, Depends(_service)]


@router.get("/catalogs/bundle", response_model=CatalogBundle)
def catalog_bundle(
    db: DbSession,
    _: CurrentUser,
    codes: str | None = Query(None, description="Códigos separados por coma; vacío = todos"),
) -> CatalogBundle:
    """Opciones activas para formularios. Disponible para cualquier usuario autenticado."""
    wanted = [c.strip() for c in codes.split(",") if c.strip()] if codes else []
    return CatalogService(SqlCatalogRepository(db)).bundle(wanted)


@router.get("/catalogs", response_model=list[CatalogRead], dependencies=[CanManage])
def list_catalogs(service: Service) -> list[CatalogRead]:
    return service.list_catalogs()


@router.get("/catalogs/{code}/options", response_model=list[CatalogOptionRead], dependencies=[CanManage])
def list_options(code: str, service: Service, include_inactive: bool = True) -> list[CatalogOptionRead]:
    return service.list_options(code, include_inactive)


@router.post(
    "/catalogs/{code}/options",
    response_model=CatalogOptionRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[CanManage],
)
def create_option(code: str, data: CatalogOptionCreate, service: Service) -> CatalogOptionRead:
    return service.create_option(code, data)


@router.put("/catalogs/{code}/order", response_model=list[CatalogOptionRead], dependencies=[CanManage])
def reorder_options(code: str, data: ReorderRequest, service: Service) -> list[CatalogOptionRead]:
    return service.reorder(code, data.option_ids)


@router.patch("/catalog-options/{option_id}", response_model=CatalogOptionRead, dependencies=[CanManage])
def update_option(option_id: UUID, data: CatalogOptionUpdate, service: Service) -> CatalogOptionRead:
    return service.update_option(option_id, data)
