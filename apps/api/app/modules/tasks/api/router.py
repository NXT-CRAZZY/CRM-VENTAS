from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from app.core.deps import CurrentUser, DbSession, require
from app.modules.audit.application.recorder import Audit
from app.modules.rbac.domain.permissions import P
from app.modules.tasks.application.use_cases import TaskService
from app.modules.tasks.repository import SqlTaskRepository
from app.modules.tasks.schemas import (
    TaskCreate,
    TaskRead,
    TaskStatusChange,
    TaskUpdate,
)
from app.shared.pagination import Page, PageParams, page_params

router = APIRouter(tags=["Tareas"])


def _service(db: DbSession, audit: Audit) -> TaskService:
    return TaskService(SqlTaskRepository(db), audit)


Service = Annotated[TaskService, Depends(_service)]


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace('Z', '+00:00'))


@router.get("/tasks", response_model=Page[TaskRead])
def list_tasks(
    service: Service,
    user: CurrentUser,
    params: Annotated[PageParams, Depends(page_params)],
    status: str | None = None,
    assignee_id: UUID | None = None,
    due_before: str | None = None,
    due_after: str | None = None,
) -> Page[TaskRead]:
    filters = {
        "status": status,
        "assignee_id": assignee_id,
        "due_before": _parse_dt(due_before),
        "due_after": _parse_dt(due_after),
    }
    return service.list_tasks({k: v for k, v in filters.items() if v is not None}, params, user)


@router.post("/tasks", response_model=TaskRead, status_code=201, dependencies=[Depends(require(P.TASKS_MANAGE))])
def create_task(data: TaskCreate, service: Service, user: CurrentUser) -> TaskRead:
    return service.create_task(data, user)


@router.patch("/tasks/{task_id}", response_model=TaskRead)
def update_task(task_id: UUID, data: TaskUpdate, service: Service, user: CurrentUser) -> TaskRead:
    return service.update_task(task_id, data, user)


@router.patch("/tasks/{task_id}/status", response_model=TaskRead)
def change_status(task_id: UUID, data: TaskStatusChange, service: Service, user: CurrentUser) -> TaskRead:
    return service.change_status(task_id, data.status, user)


@router.delete("/tasks/{task_id}", status_code=204)
def delete_task(task_id: UUID, service: Service, user: CurrentUser) -> None:
    service.delete_task(task_id, user)
