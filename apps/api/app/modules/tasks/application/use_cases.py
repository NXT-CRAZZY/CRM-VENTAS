from datetime import datetime
from uuid import UUID

from app.core.errors import ForbiddenError, NotFoundError
from app.modules.audit.application.recorder import AuditRecorder
from app.modules.rbac.domain.permissions import P
from app.modules.tasks.infrastructure.models import Task
from app.modules.tasks.repository import TaskRepository
from app.modules.tasks.schemas import TaskCreate, TaskRead, TaskUpdate
from app.modules.users.infrastructure.models import User
from app.shared.pagination import Page, PageParams


class TaskService:
    def __init__(self, repo: TaskRepository, audit: AuditRecorder | None = None) -> None:
        self.repo = repo
        self.audit = audit

    def _resolve_ids(self, data: TaskCreate | TaskUpdate) -> dict:
        resolved: dict = {}
        if hasattr(data, "assignee_id") and data.assignee_id:
            resolved["assignee_id"] = self._user(data.assignee_id)
        if hasattr(data, "type_id") and data.type_id:
            resolved["type_id"] = self._catalog(data.type_id, "tipo")
        if hasattr(data, "priority_id") and data.priority_id:
            resolved["priority_id"] = self._catalog(data.priority_id, "prioridad")
        return resolved

    def _user(self, public_id: UUID) -> int:
        internal_id = self.repo.get_user_id(public_id)
        if internal_id is None:
            raise NotFoundError("El usuario asignado no existe.")
        return internal_id

    def _catalog(self, public_id: UUID, label: str) -> int:
        internal_id = self.repo.get_catalog_option_id(public_id)
        if internal_id is None:
            raise NotFoundError(f"{label.capitalize()} no encontrado.")
        return internal_id

    def _prospect(self, public_id: UUID) -> int:
        internal_id = self.repo.get_prospect_id(public_id)
        if internal_id is None:
            raise NotFoundError("El prospecto no existe.")
        return internal_id

    def _enforce_scope(self, task: Task, user: User) -> None:
        if P.PROSPECTS_READ_ALL in user.permission_codes:
            return
        if task.assignee_id == user.id:
            return
        raise ForbiddenError("No tienes acceso a esta tarea.")

    def list_tasks(
        self, filters: dict, params: PageParams, user: User
    ) -> Page[TaskRead]:
        items, total = self.repo.list_tasks(filters, params, user)
        return Page(
            items=[TaskRead.model_validate(i) for i in items],
            total=total,
            page=params.page,
            page_size=params.page_size,
        )

    def create_task(self, data: TaskCreate, actor: User) -> Task:
        prospect_id = self._prospect(data.prospect_id)
        resolved = self._resolve_ids(data)

        task = Task(
            prospect_id=prospect_id,
            assignee_id=resolved.get("assignee_id"),
            type_id=resolved.get("type_id"),
            priority_id=resolved.get("priority_id"),
            title=data.title,
            description=data.description,
            due_at=data.due_at,
            remind_at=data.remind_at,
            status="PENDING",
        )
        self.repo.add(task)

        if self.audit:
            self.audit.record(
                "task.created",
                "task",
                task.public_id,
                label=f"Tarea: {task.title}",
                after={"prospect_id": str(data.prospect_id)},
            )

        return task

    def update_task(self, public_id: UUID, data: TaskUpdate, actor: User) -> Task:
        task = self.repo.get_task(public_id)
        if task is None:
            raise NotFoundError("La tarea no existe.")
        self._enforce_scope(task, actor)

        resolved = self._resolve_ids(data)

        if data.title is not None:
            task.title = data.title
        if data.description is not None:
            task.description = data.description
        if "assignee_id" in resolved:
            task.assignee_id = resolved["assignee_id"]
        if "type_id" in resolved:
            task.type_id = resolved["type_id"]
        if "priority_id" in resolved:
            task.priority_id = resolved["priority_id"]
        if data.due_at is not None:
            task.due_at = data.due_at
        if data.remind_at is not None:
            task.remind_at = data.remind_at

        if self.audit:
            self.audit.record(
                "task.updated",
                "task",
                task.public_id,
                label=f"Tarea: {task.title}",
            )

        return task

    def change_status(self, public_id: UUID, status: str, actor: User) -> Task:
        task = self.repo.get_task(public_id)
        if task is None:
            raise NotFoundError("La tarea no existe.")
        self._enforce_scope(task, actor)

        task.status = status
        if status == "DONE":
            task.completed_at = datetime.now()
        else:
            task.completed_at = None

        if self.audit:
            self.audit.record(
                "task.status_changed",
                "task",
                task.public_id,
                label=f"Tarea {status}: {task.title}",
            )

        return task

    def delete_task(self, public_id: UUID, actor: User) -> None:
        task = self.repo.get_task(public_id)
        if task is None:
            raise NotFoundError("La tarea no existe.")
        self._enforce_scope(task, actor)
        self.repo.delete(task)

        if self.audit:
            self.audit.record(
                "task.deleted",
                "task",
                task.public_id,
                label=f"Tarea eliminada: {task.title}",
            )
