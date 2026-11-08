from typing import Protocol
from uuid import UUID

from sqlalchemy import func, or_, select, update
from sqlalchemy.orm import Session

from app.modules.auth.infrastructure.models import RefreshToken
from app.modules.rbac.infrastructure.models import Role, user_roles
from app.modules.users.infrastructure.models import User
from app.modules.users.schemas import UserFilters
from app.shared.pagination import PageParams, paginate


class UserRepository(Protocol):
    def get(self, public_id: UUID) -> User | None: ...
    def get_by_id(self, user_id: int) -> User | None: ...
    def get_by_email(self, email: str) -> User | None: ...
    def list(self, filters: UserFilters, params: PageParams) -> tuple[list[User], int]: ...
    def count_active_with_role(self, role_code: str) -> int: ...
    def add(self, user: User) -> None: ...
    def revoke_sessions(self, user_id: int) -> None: ...


class SqlUserRepository:
    def __init__(self, session: Session) -> None:
        self.s = session

    def get(self, public_id: UUID) -> User | None:
        return self.s.scalar(select(User).where(User.public_id == public_id))

    def get_by_id(self, user_id: int) -> User | None:
        return self.s.get(User, user_id)

    def get_by_email(self, email: str) -> User | None:
        return self.s.scalar(select(User).where(func.lower(User.email) == email.lower()))

    def list(self, filters: UserFilters, params: PageParams) -> tuple[list[User], int]:
        stmt = select(User).order_by(User.full_name)
        if filters.status == "active":
            stmt = stmt.where(User.is_active.is_(True))
        elif filters.status == "inactive":
            stmt = stmt.where(User.is_active.is_(False))
        if filters.q:
            like = f"%{filters.q.strip()}%"
            stmt = stmt.where(or_(User.full_name.ilike(like), User.email.ilike(like)))
        if filters.role_id:
            stmt = stmt.where(
                User.id.in_(
                    select(user_roles.c.user_id)
                    .join(Role, Role.id == user_roles.c.role_id)
                    .where(Role.public_id == filters.role_id)
                )
            )
        return paginate(self.s, stmt, params)

    def count_active_with_role(self, role_code: str) -> int:
        stmt = (
            select(func.count(func.distinct(User.id)))
            .join(user_roles, user_roles.c.user_id == User.id)
            .join(Role, Role.id == user_roles.c.role_id)
            .where(Role.code == role_code, User.is_active.is_(True))
        )
        return self.s.scalar(stmt) or 0

    def add(self, user: User) -> None:
        self.s.add(user)
        self.s.flush()

    def revoke_sessions(self, user_id: int) -> None:
        self.s.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=func.now())
        )
