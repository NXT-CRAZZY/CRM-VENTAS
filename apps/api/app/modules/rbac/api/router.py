from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.core.deps import DbSession, require
from app.modules.audit.application.recorder import Audit
from app.modules.rbac.application.use_cases import RoleService
from app.modules.rbac.domain.permissions import P
from app.modules.rbac.repository import SqlRoleRepository
from app.modules.rbac.schemas import PermissionGroup, RoleCreate, RoleRead, RoleUpdate

router = APIRouter(tags=["Roles y permisos"])


def _service(db: DbSession, audit: Audit) -> RoleService:
    return RoleService(SqlRoleRepository(db), audit)


Service = Annotated[RoleService, Depends(_service)]
CanRead = Depends(require(P.ROLES_READ))
CanManage = Depends(require(P.ROLES_MANAGE))


@router.get("/permissions", response_model=list[PermissionGroup], dependencies=[CanRead])
def list_permissions(service: Service) -> list[PermissionGroup]:
    return service.permission_groups()


@router.get("/roles", response_model=list[RoleRead], dependencies=[CanRead])
def list_roles(service: Service) -> list[RoleRead]:
    return service.list_roles()


@router.post("/roles", response_model=RoleRead, status_code=status.HTTP_201_CREATED, dependencies=[CanManage])
def create_role(data: RoleCreate, service: Service) -> RoleRead:
    return service.create(data)


@router.patch("/roles/{role_id}", response_model=RoleRead, dependencies=[CanManage])
def update_role(role_id: UUID, data: RoleUpdate, service: Service) -> RoleRead:
    return service.update(role_id, data)


@router.delete("/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[CanManage])
def delete_role(role_id: UUID, service: Service) -> None:
    service.delete(role_id)
