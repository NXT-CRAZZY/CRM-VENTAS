from itertools import groupby
from uuid import UUID

from app.core.errors import AppError, ConflictError, NotFoundError
from app.modules.audit.application.recorder import AuditRecorder, diff
from app.modules.rbac.domain.permissions import ALL_CODES
from app.modules.rbac.infrastructure.models import Role
from app.modules.rbac.repository import RoleRepository
from app.modules.rbac.schemas import PermissionGroup, PermissionRead, RoleCreate, RoleRead, RoleUpdate
from app.shared.text import slug_code


def _snapshot(role: Role) -> dict:
    return {
        "name": role.name,
        "description": role.description,
        "permissions": sorted(p.code for p in role.permissions),
    }


class RoleService:
    """Casos de uso de roles y permisos."""

    def __init__(self, repo: RoleRepository, audit: AuditRecorder | None = None) -> None:
        self.repo = repo
        self.audit = audit

    def _to_read(self, role: Role) -> RoleRead:
        data = RoleRead.model_validate(role)
        data.user_count = self.repo.count_users(role.id)
        return data

    def permission_groups(self) -> list[PermissionGroup]:
        perms = self.repo.list_permissions()
        return [
            PermissionGroup(module=module, permissions=[PermissionRead.model_validate(p) for p in items])
            for module, items in groupby(perms, key=lambda p: p.module)
        ]

    def list_roles(self) -> list[RoleRead]:
        return [self._to_read(r) for r in self.repo.list_roles()]

    def _get(self, role_id: UUID) -> Role:
        role = self.repo.get_role(role_id)
        if role is None:
            raise NotFoundError("El rol no existe.")
        return role

    def _resolve_permissions(self, codes: list[str]) -> list:
        unknown = sorted(set(codes) - set(ALL_CODES))
        if unknown:
            raise AppError("Hay permisos no reconocidos.", code="UNKNOWN_PERMISSION", details=unknown)
        return self.repo.get_permissions(sorted(set(codes)))

    def create(self, data: RoleCreate) -> RoleRead:
        if self.repo.get_role_by_name(data.name):
            raise ConflictError("Ya existe un rol con ese nombre.", code="ROLE_NAME_TAKEN")
        code = slug_code(data.name) or "ROL"
        if self.repo.get_role_by_code(code):
            code = f"{code[:34]}_{len(self.repo.list_roles())}"
        role = Role(
            code=code,
            name=data.name.strip(),
            description=data.description,
            is_system=False,
            permissions=self._resolve_permissions(data.permissions),
        )
        self.repo.add(role)
        if self.audit:
            self.audit.record("role.created", "role", role.public_id, label=role.name, after=_snapshot(role))
        return self._to_read(role)

    def update(self, role_id: UUID, data: RoleUpdate) -> RoleRead:
        role = self._get(role_id)
        before = _snapshot(role)
        if data.name is not None and data.name.strip() != role.name:
            other = self.repo.get_role_by_name(data.name)
            if other and other.id != role.id:
                raise ConflictError("Ya existe un rol con ese nombre.", code="ROLE_NAME_TAKEN")
            role.name = data.name.strip()
        if "description" in data.model_fields_set:
            role.description = data.description
        if data.permissions is not None:
            if role.code == "ADMIN":
                raise AppError("Los permisos del rol Administrador no se pueden reducir.", code="ADMIN_ROLE_LOCKED")
            role.permissions = self._resolve_permissions(data.permissions)
        self.repo.add(role)
        if self.audit:
            b, a = diff(before, _snapshot(role))
            if a:
                self.audit.record("role.updated", "role", role.public_id, label=role.name, before=b, after=a)
        return self._to_read(role)

    def delete(self, role_id: UUID) -> None:
        role = self._get(role_id)
        if role.is_system:
            raise AppError("Los roles del sistema no se pueden eliminar.", code="SYSTEM_ROLE")
        if self.repo.count_users(role.id):
            raise ConflictError("El rol tiene usuarios asignados. Reasígnalos antes de eliminarlo.", code="ROLE_IN_USE")
        if self.audit:
            self.audit.record("role.deleted", "role", role.public_id, label=role.name, before=_snapshot(role))
        self.repo.delete(role)
