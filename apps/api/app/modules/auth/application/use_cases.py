import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from app.core.config import get_settings
from app.core.errors import AppError, TooManyRequestsError, UnauthorizedError
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.modules.audit.application.recorder import AuditRecorder
from app.modules.auth.infrastructure.models import RefreshToken
from app.modules.auth.repository import RefreshTokenRepository
from app.modules.auth.schemas import ChangePasswordRequest, SessionUser, TokenResponse
from app.modules.users.infrastructure.models import User
from app.modules.users.repository import UserRepository

INVALID_CREDENTIALS = "Correo o contraseña incorrectos."


@dataclass
class IssuedSession:
    response: TokenResponse
    refresh_token: str


class AuthService:
    def __init__(
        self,
        users: UserRepository,
        tokens: RefreshTokenRepository,
        audit_factory: Callable[[int | None], AuditRecorder],
        commit: Callable[[], None],
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        self.users = users
        self.tokens = tokens
        self.audit_factory = audit_factory
        # Algunos efectos (intentos fallidos, revocación por reutilización) deben persistir
        # aunque la respuesta sea un error; por eso se confirman antes de lanzar la excepción.
        self.commit = commit
        self.ip = ip
        self.user_agent = user_agent
        self.settings = get_settings()

    def _audit(self, user_id: int | None) -> AuditRecorder:
        return self.audit_factory(user_id)

    def _issue(self, user: User, family_id: uuid.UUID | None = None) -> IssuedSession:
        access, expires_in = create_access_token(user.public_id)
        raw_refresh = generate_refresh_token()
        self.tokens.add(
            RefreshToken(
                user_id=user.id,
                token_hash=hash_token(raw_refresh),
                family_id=family_id or uuid.uuid4(),
                expires_at=datetime.now(UTC) + timedelta(days=self.settings.refresh_token_days),
                ip=self.ip,
                user_agent=self.user_agent,
            )
        )
        return IssuedSession(
            response=TokenResponse(access_token=access, expires_in=expires_in, user=SessionUser.model_validate(user)),
            refresh_token=raw_refresh,
        )

    def login(self, email: str, password: str) -> IssuedSession:
        now = datetime.now(UTC)
        user = self.users.get_by_email(email)
        if user is None:
            # Se verifica un hash ficticio para no revelar por tiempos si el correo existe.
            verify_password(password, _DUMMY_HASH)
            raise UnauthorizedError(INVALID_CREDENTIALS, code="INVALID_CREDENTIALS")
        if user.locked_until and user.locked_until > now:
            minutes = max(1, int((user.locked_until - now).total_seconds() // 60) + 1)
            raise TooManyRequestsError(
                f"Demasiados intentos fallidos. Intenta nuevamente en {minutes} minuto(s).",
                code="ACCOUNT_LOCKED",
            )
        if not verify_password(password, user.password_hash):
            user.failed_login_count += 1
            if user.failed_login_count >= self.settings.max_failed_logins:
                user.locked_until = now + timedelta(minutes=self.settings.lockout_minutes)
                user.failed_login_count = 0
                self._audit(user.id).record("auth.locked", "user", user.public_id, label=user.full_name)
            self.users.add(user)
            self.commit()
            raise UnauthorizedError(INVALID_CREDENTIALS, code="INVALID_CREDENTIALS")
        if not user.is_active:
            raise UnauthorizedError("Tu usuario está desactivado. Consulta con el administrador.", code="USER_INACTIVE")

        user.failed_login_count = 0
        user.locked_until = None
        user.last_login_at = now
        self.users.add(user)
        self._audit(user.id).record("auth.login", "user", user.public_id, label=user.full_name)
        return self._issue(user)

    def refresh(self, raw_token: str | None) -> IssuedSession:
        if not raw_token:
            raise UnauthorizedError("Tu sesión expiró. Inicia sesión nuevamente.", code="NO_REFRESH_TOKEN")
        stored = self.tokens.get_by_hash(hash_token(raw_token))
        if stored is None:
            raise UnauthorizedError("Tu sesión expiró. Inicia sesión nuevamente.", code="REFRESH_INVALID")
        if stored.revoked_at is not None:
            # Reutilización de un token ya rotado: se invalida toda la sesión.
            self.tokens.revoke_family(stored.family_id)
            self._audit(stored.user_id).record("auth.refresh_reuse", "user", None)
            self.commit()
            raise UnauthorizedError(
                "Tu sesión fue cerrada por seguridad. Inicia sesión nuevamente.", code="REFRESH_REUSED"
            )
        if stored.expires_at <= datetime.now(UTC):
            raise UnauthorizedError("Tu sesión expiró. Inicia sesión nuevamente.", code="REFRESH_EXPIRED")

        user = self.users.get_by_id(stored.user_id)
        if user is None or not user.is_active:
            self.tokens.revoke_family(stored.family_id)
            self.commit()
            raise UnauthorizedError("Tu usuario no está activo.", code="USER_INACTIVE")

        stored.revoked_at = datetime.now(UTC)
        self.tokens.add(stored)
        return self._issue(user, family_id=stored.family_id)

    def logout(self, raw_token: str | None) -> None:
        if not raw_token:
            return
        stored = self.tokens.get_by_hash(hash_token(raw_token))
        if stored is not None:
            self.tokens.revoke_family(stored.family_id)
            self._audit(stored.user_id).record("auth.logout", "user", None)

    def change_password(self, user: User, data: ChangePasswordRequest) -> None:
        if not verify_password(data.current_password, user.password_hash):
            raise AppError("La contraseña actual no es correcta.", code="WRONG_PASSWORD")
        if data.current_password == data.new_password:
            raise AppError("La nueva contraseña debe ser distinta de la actual.", code="SAME_PASSWORD")
        user.password_hash = hash_password(data.new_password)
        user.must_change_password = False
        self.users.add(user)
        self._audit(user.id).record("auth.password_changed", "user", user.public_id, label=user.full_name)


_DUMMY_HASH = hash_password("dummy-password-for-timing")
