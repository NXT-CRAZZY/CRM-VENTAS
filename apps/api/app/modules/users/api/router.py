from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.core.deps import CurrentUser, DbSession, require
from app.modules.audit.application.recorder import Audit
from app.modules.rbac.domain.permissions import P
from app.modules.rbac.repository import SqlRoleRepository
from app.modules.users.application.use_cases import UserService
from app.modules.users.repository import SqlUserRepository
from app.modules.users.schemas import PasswordReset, UserCreate, UserFilters, UserRead, UserUpdate
from app.shared.pagination import Page, PageParams, page_params

router = APIRouter(prefix="/users", tags=["Usuarios"])


def _service(db: DbSession, audit: Audit, actor: CurrentUser) -> UserService:
    return UserService(SqlUserRepository(db), SqlRoleRepository(db), audit, actor)


Service = Annotated[UserService, Depends(_service)]
CanRead = Depends(require(P.USERS_READ))
CanManage = Depends(require(P.USERS_MANAGE))


@router.get("", response_model=Page[UserRead], dependencies=[CanRead])
def list_users(
    service: Service,
    params: Annotated[PageParams, Depends(page_params)],
    q: str | None = Query(None, description="Busca por nombre o correo"),
    status_: Literal["active", "inactive", "all"] = Query("active", alias="status"),
    role_id: UUID | None = None,
) -> Page[UserRead]:
    return service.list(UserFilters(q=q, status=status_, role_id=role_id), params)


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED, dependencies=[CanManage])
def create_user(data: UserCreate, service: Service) -> UserRead:
    return service.create(data)


@router.get("/{user_id}", response_model=UserRead, dependencies=[CanRead])
def get_user(user_id: UUID, service: Service) -> UserRead:
    return service.get(user_id)


@router.patch("/{user_id}", response_model=UserRead, dependencies=[CanManage])
def update_user(user_id: UUID, data: UserUpdate, service: Service) -> UserRead:
    return service.update(user_id, data)


@router.post("/{user_id}/deactivate", response_model=UserRead, dependencies=[CanManage])
def deactivate_user(user_id: UUID, service: Service) -> UserRead:
    return service.deactivate(user_id)


@router.post("/{user_id}/activate", response_model=UserRead, dependencies=[CanManage])
def activate_user(user_id: UUID, service: Service) -> UserRead:
    return service.activate(user_id)


@router.post("/{user_id}/reset-password", status_code=status.HTTP_204_NO_CONTENT, dependencies=[CanManage])
def reset_password(user_id: UUID, data: PasswordReset, service: Service) -> None:
    service.reset_password(user_id, data)
