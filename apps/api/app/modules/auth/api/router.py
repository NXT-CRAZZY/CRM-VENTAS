from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status

from app.core.config import get_settings
from app.core.deps import CurrentUser, DbSession, ReqCtx
from app.core.rate_limit import limiter
from app.modules.audit.application.recorder import SqlAuditRecorder
from app.modules.auth.application.use_cases import AuthService, IssuedSession
from app.modules.auth.repository import SqlRefreshTokenRepository
from app.modules.auth.schemas import ChangePasswordRequest, LoginRequest, SessionUser, TokenResponse
from app.modules.users.repository import SqlUserRepository

router = APIRouter(prefix="/auth", tags=["Autenticación"])
settings = get_settings()
COOKIE_PATH = f"{settings.api_prefix}/auth"


def _service(db: DbSession, ctx: ReqCtx) -> AuthService:
    return AuthService(
        SqlUserRepository(db),
        SqlRefreshTokenRepository(db),
        lambda user_id: SqlAuditRecorder(db, user_id, ctx.ip, ctx.user_agent),
        commit=db.commit,
        ip=ctx.ip,
        user_agent=ctx.user_agent,
    )


Service = Annotated[AuthService, Depends(_service)]


def _set_refresh_cookie(response: Response, session: IssuedSession) -> TokenResponse:
    response.set_cookie(
        key=settings.refresh_cookie_name,
        value=session.refresh_token,
        max_age=settings.refresh_token_days * 24 * 3600,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="strict",
        path=COOKIE_PATH,
    )
    return session.response


@router.post("/login", response_model=TokenResponse)
@limiter.limit(settings.login_rate_limit)
def login(request: Request, response: Response, data: LoginRequest, service: Service) -> TokenResponse:
    return _set_refresh_cookie(response, service.login(data.email, data.password))


@router.post("/refresh", response_model=TokenResponse)
def refresh(request: Request, response: Response, service: Service) -> TokenResponse:
    return _set_refresh_cookie(response, service.refresh(request.cookies.get(settings.refresh_cookie_name)))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, response: Response, service: Service) -> None:
    service.logout(request.cookies.get(settings.refresh_cookie_name))
    response.delete_cookie(settings.refresh_cookie_name, path=COOKIE_PATH)


@router.get("/me", response_model=SessionUser)
def me(user: CurrentUser) -> SessionUser:
    return SessionUser.model_validate(user)


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(data: ChangePasswordRequest, user: CurrentUser, service: Service) -> None:
    service.change_password(user, data)
