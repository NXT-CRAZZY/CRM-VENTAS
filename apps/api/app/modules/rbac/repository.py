from typing import Protocol
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.rbac.infrastructure.models import Permission, Role, user_roles


class RoleRepository(Protocol):
    def list_roles(self) -> list[Role]: ...
    def get_role(self, public_id: UUID) -> Role | None: ...
    def get_roles(self, public_ids: list[UUID]) -> list[Role]: ...
    def get_role_by_name(self, name: str) -> Role | None: ...
    def get_role_by_code(self, code: str) -> Role | None: ...
    def list_permissions(self) -> list[Permission]: ...
    def get_permissions(self, codes: list[str]) -> list[Permission]: ...
    def count_users(self, role_id: int) -> int: ...
    def add(self, role: Role) -> None: ...
    def delete(self, role: Role) -> None: ...


class SqlRoleRepository:
    def __init__(self, session: Session) -> None:
        self.s = session

    def list_roles(self) -> list[Role]:
        return list(self.s.scalars(select(Role).order_by(Role.is_system.desc(), Role.name)))

    def get_role(self, public_id: UUID) -> Role | None:
        return self.s.scalar(select(Role).where(Role.public_id == public_id))

    def get_roles(self, public_ids: list[UUID]) -> list[Role]:
        if not public_ids:
            return []
        return list(self.s.scalars(select(Role).where(Role.public_id.in_(public_ids))))

    def get_role_by_name(self, name: str) -> Role | None:
        return self.s.scalar(select(Role).where(func.lower(Role.name) == name.lower()))

    def get_role_by_code(self, code: str) -> Role | None:
        return self.s.scalar(select(Role).where(Role.code == code))

    def list_permissions(self) -> list[Permission]:
        return list(self.s.scalars(select(Permission).order_by(Permission.module, Permission.code)))

    def get_permissions(self, codes: list[str]) -> list[Permission]:
        if not codes:
            return []
        return list(self.s.scalars(select(Permission).where(Permission.code.in_(codes))))

    def count_users(self, role_id: int) -> int:
        return self.s.scalar(select(func.count()).select_from(user_roles).where(user_roles.c.role_id == role_id)) or 0

    def add(self, role: Role) -> None:
        self.s.add(role)
        self.s.flush()

    def delete(self, role: Role) -> None:
        self.s.delete(role)
        self.s.flush()
