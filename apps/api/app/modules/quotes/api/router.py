from datetime import date
from typing import Annotated, Literal, cast
from uuid import UUID

from fastapi import APIRouter, Depends

from app.core.deps import CurrentUser, DbSession, require
from app.modules.audit.application.recorder import Audit
from app.modules.quotes.application.use_cases import QuoteService
from app.modules.quotes.repository import SqlQuoteRepository
from app.modules.quotes.schemas import (
    QuoteCreate,
    QuoteRead,
    QuoteStatusChange,
    QuoteUpdate,
)
from app.modules.rbac.domain.permissions import P
from app.modules.settings.application.use_cases import SettingsService
from app.modules.settings.domain.registry import AlertSettings
from app.shared.pagination import Page, PageParams, page_params

router = APIRouter(tags=["Cotizaciones"])


def _service(db: DbSession, audit: Audit) -> QuoteService:
    settings = cast(AlertSettings, SettingsService(db).get("alerts"))
    return QuoteService(SqlQuoteRepository(db), audit, settings)


Service = Annotated[QuoteService, Depends(_service)]


@router.get("/quotes", response_model=Page[QuoteRead])
def list_quotes(
    service: Service,
    user: CurrentUser,
    params: Annotated[PageParams, Depends(page_params)],
    status: str | None = None,
    prospect_id: UUID | None = None,
    opportunity_id: UUID | None = None,
    search: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    owner_id: UUID | None = None,
    product_id: UUID | None = None,
    sort: Literal["newest", "oldest", "amount_desc", "amount_asc", "expiring"] = "newest",
) -> Page[QuoteRead]:
    filters = {
        "status": status,
        "prospect_id": prospect_id,
        "opportunity_id": opportunity_id,
        "search": search,
        "date_from": date_from,
        "date_to": date_to,
        "owner_id": owner_id,
        "product_id": product_id,
        "sort": sort,
    }
    return service.list_quotes({k: v for k, v in filters.items() if v is not None}, params, user)


@router.post(
    "/quotes",
    response_model=QuoteRead,
    status_code=201,
    dependencies=[Depends(require(P.QUOTES_MANAGE))],
)
def create_quote(data: QuoteCreate, service: Service, user: CurrentUser) -> QuoteRead:
    return service.create_quote(data, user)


@router.patch("/quotes/{quote_id}", response_model=QuoteRead)
def update_quote(quote_id: UUID, data: QuoteUpdate, service: Service, user: CurrentUser) -> QuoteRead:
    return service.update_quote(quote_id, data, user)


@router.patch("/quotes/{quote_id}/status", response_model=QuoteRead)
def change_status(quote_id: UUID, data: QuoteStatusChange, service: Service, user: CurrentUser) -> QuoteRead:
    return service.change_status(quote_id, data, user)


@router.delete("/quotes/{quote_id}", status_code=204)
def delete_quote(quote_id: UUID, service: Service, user: CurrentUser) -> None:
    service.delete_quote(quote_id, user)
