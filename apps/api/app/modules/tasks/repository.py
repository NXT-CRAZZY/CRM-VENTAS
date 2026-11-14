from typing import Protocol
from uuid import UUID

from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.modules.catalogs.infrastructure.models import Catalog, CatalogOption
from app.modules.tasks.infrastructure.models import Task
from app.modules.users.infrastructure.models import User
from app.shared.pagination import PageParams, paginate


class TaskRepository(Protocol):
    def list_tasks(self, filters: dict, params: PageParams, user: User) -> tuple[list[Task], int]: ...
    def get_task(self, public_id: UUID) -> Task | None: ...
    def add(self, task: Task) -> None: ...
    def delete(self, task: Task) -> None: ...
    def get_prospect_id(self, public_id: UUID) -> int | None: ...
    def get_user_id(self, public_id: UUID) -> int | None: ...
    def get_catalog_option_id(self, public_id: UUID) -> int | None: ...
    def get_catalog_option_id_by_code(self, catalog_code: str, option_code: str) -> int | None: ...


class SqlTaskRepository:
    def __init__(self, session: Session) -> None:
        self.s = session

    def _base_query(self) -> select:
        return (
            select(Task)
            .where(Task.deleted_at.is_(None))
            .options(
                selectinload(Task.assignee),
                selectinload(Task.type),
                selectinload(Task.priority),
                selectinload(Task.prospect),
            )
        )

    def list_tasks(self, filters: dict, params: PageParams, user: User) -> tuple[list[Task], int]:
        from app.modules.rbac.domain.permissions import P

        stmt = self._base_query()
        if P.PROSPECTS_READ_ALL not in user.permission_codes:
            stmt = stmt.where(Task.assignee_id == user.id)
        if filters.get("status"):
            stmt = stmt.where(Task.status == filters["status"])
        if filters.get("assignee_id") and P.PROSPECTS_READ_ALL in user.permission_codes:
            assignee = self.get_user_id(filters["assignee_id"])
            stmt = stmt.where(Task.assignee_id == (assignee if assignee is not None else -1))
        if filters.get("type_id"):
            type_id = self.get_catalog_option_id(filters["type_id"])
            stmt = stmt.where(Task.type_id == (type_id if type_id is not None else -1))
        if filters.get("priority_id"):
            priority_id = self.get_catalog_option_id(filters["priority_id"])
            stmt = stmt.where(Task.priority_id == (priority_id if priority_id is not None else -1))
        if filters.get("search"):
            from app.modules.prospects.infrastructure.models import Prospect

            like = f"%{filters['search'].strip()}%"
            stmt = stmt.where(
                or_(
                    Task.title.ilike(like),
                    Task.description.ilike(like),
                    Task.prospect.has(
                        or_(Prospect.display_name.ilike(like), Prospect.document_number.ilike(like))
                    ),
                )
            )
        if filters.get("prospect_id"):
            from app.modules.prospects.infrastructure.models import Prospect

            stmt = stmt.where(
                Task.prospect_id == select(Prospect.id).where(Prospect.public_id == filters["prospect_id"]).scalar_subquery()
            )
        if filters.get("due_before"):
            stmt = stmt.where(Task.due_at <= filters["due_before"])
        if filters.get("due_after"):
            stmt = stmt.where(Task.due_at >= filters["due_after"])
        sort = filters.get("sort", "due_asc")
        if sort == "due_desc":
            stmt = stmt.order_by(Task.due_at.desc().nullslast(), Task.created_at.desc())
        elif sort == "newest":
            stmt = stmt.order_by(Task.created_at.desc())
        elif sort == "priority":
            weight = (
                select(
                    case(
                        (CatalogOption.code == "ALTA", 0),
                        (CatalogOption.code == "MEDIA", 1),
                        (CatalogOption.code == "BAJA", 2),
                        else_=3,
                    )
                )
                .where(CatalogOption.id == Task.priority_id)
                .scalar_subquery()
            )
            stmt = stmt.order_by(func.coalesce(weight, 3), Task.due_at.asc().nullslast())
        else:
            stmt = stmt.order_by(Task.due_at.asc().nullslast(), Task.created_at.desc())
        return paginate(self.s, stmt, params)

    def get_task(self, public_id: UUID) -> Task | None:
        return self.s.scalar(self._base_query().where(Task.public_id == public_id))

    def add(self, task: Task) -> None:
        self.s.add(task)
        self.s.flush()

    def delete(self, task: Task) -> None:
        task.deleted_at = func.now()

    def get_prospect_id(self, public_id: UUID) -> int | None:
        from app.modules.prospects.infrastructure.models import Prospect

        return self.s.scalar(select(Prospect.id).where(Prospect.public_id == public_id))

    def get_user_id(self, public_id: UUID) -> int | None:
        return self.s.scalar(select(User.id).where(User.public_id == public_id))

    def get_catalog_option_id(self, public_id: UUID) -> int | None:
        return self.s.scalar(select(CatalogOption.id).where(CatalogOption.public_id == public_id))

    def get_catalog_option_id_by_code(self, catalog_code: str, option_code: str) -> int | None:
        return self.s.scalar(
            select(CatalogOption.id)
            .join(Catalog, Catalog.id == CatalogOption.catalog_id)
            .where(Catalog.code == catalog_code, CatalogOption.code == option_code)
        )
