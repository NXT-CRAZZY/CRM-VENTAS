from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID

from app.core.errors import AppError, ConflictError, NotFoundError
from app.core.security import hash_password
from app.modules.audit.application.recorder import AuditRecorder, diff
from app.modules.rbac.repository import RoleRepository
from app.modules.users.infrastructure.models import User
from app.modules.users.repository import UserRepository
from app.modules.users.schemas import PasswordReset, UserCreate, UserFilters, UserRead, UserUpdate
from app.shared.pagination import Page, PageParams

# Gancho para la fase 2: antes de desactivar se verificará que no tenga prospectos,
# oportunidades abiertas ni tareas pendientes sin reasignar.
DeactivationGuard = Callable[[User], None]


def _snapshot(user: User) -> dict:
    return {
        "email": user.email,
        "full_name": user.full_name,
        "phone": user.phone,
        "is_active": user.is_active,
        "roles": sorted(r.code for r in user.roles),
    }


class UserService:
    def __init__(
        self,
        users: UserRepository,
        roles: RoleRepository,
        audit: AuditRecorder,
        actor: User,
        deactivation_guards: list[DeactivationGuard] | None = None,
    ) -> None:
        self.users = users
        self.roles = roles
        self.audit = audit
        self.actor = actor
        self.deactivation_guards = deactivation_guards or []

    def _get(self, user_id: UUID) -> User:
        user = self.users.get(user_id)
        if user is None:
            raise NotFoundError("El usuario no existe.")
        return user

    def _resolve_roles(self, role_ids: list[UUID]) -> list:
        roles = self.roles.get_roles(role_ids)
        if len(roles) != len(set(role_ids)):
            raise AppError("Uno de los roles seleccionados no existe.", code="ROLE_NOT_FOUND")
        return roles

    def _ensure_email_free(self, email: str, exclude_id: int | None = None) -> None:
        other = self.users.get_by_email(email)
        if other and other.id != exclude_id:
            raise ConflictError("Ya existe un usuario con ese correo.", code="EMAIL_TAKEN")

    def _ensure_admin_remains(self, user: User) -> None:
        if "ADMIN" in user.role_codes and user.is_active and self.users.count_active_with_role("ADMIN") <= 1:
            raise AppError("Debe existir al menos un administrador activo.", code="LAST_ADMIN")

    def list(self, filters: UserFilters, params: PageParams) -> Page[UserRead]:
        items, total = self.users.list(filters, params)
        return Page[UserRead](
            items=[UserRead.model_validate(u) for u in items],
            total=total,
            page=params.page,
            page_size=params.page_size,
        )

    def get(self, user_id: UUID) -> UserRead:
        return UserRead.model_validate(self._get(user_id))

    def create(self, data: UserCreate) -> UserRead:
        email = data.email.lower()
        self._ensure_email_free(email)
        user = User(
            email=email,
            full_name=data.full_name.strip(),
            phone=data.phone,
            password_hash=hash_password(data.password),
            must_change_password=True,
            roles=self._resolve_roles(data.role_ids),
        )
        self.users.add(user)
        self.audit.record("user.created", "user", user.public_id, label=user.full_name, after=_snapshot(user))
        return UserRead.model_validate(user)

    def update(self, user_id: UUID, data: UserUpdate) -> UserRead:
        user = self._get(user_id)
        before = _snapshot(user)
        if data.email is not None:
            self._ensure_email_free(data.email, exclude_id=user.id)
            user.email = data.email.lower()
        if data.full_name is not None:
            user.full_name = data.full_name.strip()
        if "phone" in data.model_fields_set:
            user.phone = data.phone
        if data.role_ids is not None:
            new_roles = self._resolve_roles(data.role_ids)
            if "ADMIN" not in {r.code for r in new_roles}:
                self._ensure_admin_remains(user)
            user.roles = new_roles
        self.users.add(user)
        b, a = diff(before, _snapshot(user))
        if a:
            action = "user.roles_changed" if "roles" in a else "user.updated"
            self.audit.record(action, "user", user.public_id, label=user.full_name, before=b, after=a)
        return UserRead.model_validate(user)

    def deactivate(self, user_id: UUID) -> UserRead:
        user = self._get(user_id)
        if user.id == self.actor.id:
            raise AppError("No puedes desactivar tu propio usuario.", code="SELF_DEACTIVATION")
        if not user.is_active:
            return UserRead.model_validate(user)
        self._ensure_admin_remains(user)
        for guard in self.deactivation_guards:
            guard(user)
        user.is_active = False
        user.deactivated_at = datetime.now(UTC)
        self.users.revoke_sessions(user.id)
        self.users.add(user)
        self.audit.record("user.deactivated", "user", user.public_id, label=user.full_name)
        return UserRead.model_validate(user)

    def activate(self, user_id: UUID) -> UserRead:
        user = self._get(user_id)
        if user.is_active:
            return UserRead.model_validate(user)
        user.is_active = True
        user.deactivated_at = None
        user.failed_login_count = 0
        user.locked_until = None
        self.users.add(user)
        self.audit.record("user.activated", "user", user.public_id, label=user.full_name)
        return UserRead.model_validate(user)

    def reset_password(self, user_id: UUID, data: PasswordReset) -> None:
        user = self._get(user_id)
        user.password_hash = hash_password(data.password)
        user.must_change_password = True
        user.failed_login_count = 0
        user.locked_until = None
        self.users.revoke_sessions(user.id)
        self.users.add(user)
        self.audit.record("user.password_reset", "user", user.public_id, label=user.full_name)
