import uuid
from collections.abc import Callable
from dataclasses import dataclass
from typing import Annotated

import jwt
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.errors import ForbiddenError, UnauthorizedError
from app.core.security import decode_access_token
from app.modules.users.infrastructure.models import User

_bearer = HTTPBearer(auto_error=False)

DbSession = Annotated[Session, Depends(get_db)]


@dataclass(frozen=True)
class RequestContext:
    ip: str | None
    user_agent: str | None


def get_request_context(request: Request) -> RequestContext:
    forwarded = request.headers.get("x-forwarded-for")
    ip = forwarded.split(",")[0].strip() if forwarded else (request.client.host if request.client else None)
    return RequestContext(ip=ip, user_agent=(request.headers.get("user-agent") or "")[:255] or None)


ReqCtx = Annotated[RequestContext, Depends(get_request_context)]


def get_current_user(
    db: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> User:
    if credentials is None:
        raise UnauthorizedError("Debes iniciar sesión.", code="NOT_AUTHENTICATED")
    try:
        payload = decode_access_token(credentials.credentials)
        public_id = uuid.UUID(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError) as exc:
        raise UnauthorizedError("Tu sesión expiró. Inicia sesión nuevamente.", code="TOKEN_INVALID") from exc
    user = db.scalar(select(User).where(User.public_id == public_id))
    if user is None or not user.is_active:
        raise UnauthorizedError("Tu usuario no está activo.", code="USER_INACTIVE")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require(*codes: str) -> Callable[[User], User]:
    """Dependencia que exige TODOS los permisos indicados. Se valida siempre en backend."""

    def _checker(user: CurrentUser) -> User:
        missing = [c for c in codes if c not in user.permission_codes]
        if missing:
            raise ForbiddenError("No tienes permiso para realizar esta acción.", details={"missing": missing})
        return user

    return _checker


def require_any(*codes: str) -> Callable[[User], User]:
    def _checker(user: CurrentUser) -> User:
        if not user.permission_codes.intersection(codes):
            raise ForbiddenError("No tienes permiso para realizar esta acción.")
        return user

    return _checker
