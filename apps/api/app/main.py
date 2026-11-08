from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text
from starlette.requests import Request
from starlette.responses import JSONResponse

import app.core.models_registry  # noqa: F401  (registra todos los modelos)
from app.core.config import get_settings
from app.core.db import SessionLocal
from app.core.errors import register_error_handlers
from app.core.logging import RequestLogMiddleware, configure_logging
from app.core.rate_limit import limiter
from app.modules.alerts.api.router import router as alerts_router
from app.modules.audit.api.router import router as audit_router
from app.modules.auth.api.router import router as auth_router
from app.modules.catalogs.api.router import router as catalogs_router
from app.modules.dashboard.api.router import router as dashboard_router
from app.modules.imports.api.router import router as imports_router
from app.modules.interactions.api.router import router as interactions_router
from app.modules.opportunities.api.router import router as opportunities_router
from app.modules.products.api.router import router as products_router
from app.modules.prospects.api.router import router as prospects_router
from app.modules.quotes.api.router import router as quotes_router
from app.modules.rbac.api.router import router as rbac_router
from app.modules.scoring.api.router import router as scoring_router
from app.modules.settings.api.router import router as settings_router
from app.modules.tasks.api.router import router as tasks_router
from app.modules.users.api.router import router as users_router


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging()

    app = FastAPI(
        title="CRM DATA SERVICE — API",
        version="0.1.0",
        description="API del CRM comercial de DATA SERVICE.",
        docs_url="/api/docs",
        redoc_url=None,
        openapi_url="/api/openapi.json",
    )
    app.state.limiter = limiter

    @app.exception_handler(RateLimitExceeded)
    async def _rate_limited(_: Request, __: RateLimitExceeded) -> JSONResponse:
        return JSONResponse(
            status_code=429,
            content={
                "error": {
                    "code": "TOO_MANY_REQUESTS",
                    "message": "Demasiados intentos. Espera un momento e inténtalo de nuevo.",
                    "details": None,
                }
            },
        )

    register_error_handlers(app)
    app.add_middleware(RequestLogMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    api = APIRouter(prefix=settings.api_prefix)
    for router in (
        auth_router,
        users_router,
        rbac_router,
        catalogs_router,
        dashboard_router,
        products_router,
        prospects_router,
        interactions_router,
        tasks_router,
        opportunities_router,
        quotes_router,
        imports_router,
        alerts_router,
        scoring_router,
        settings_router,
        audit_router,
    ):
        api.include_router(router)
    app.include_router(api)

    @app.get("/api/health", tags=["Sistema"])
    def health() -> dict[str, str]:
        with SessionLocal() as session:
            session.execute(text("SELECT 1"))
        return {"status": "ok"}

    return app


app = create_app()
