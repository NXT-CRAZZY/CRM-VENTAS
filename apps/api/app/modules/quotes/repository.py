from typing import Protocol
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.modules.catalogs.infrastructure.models import CatalogOption
from app.modules.products.infrastructure.models import Product
from app.modules.prospects.infrastructure.models import Prospect
from app.modules.quotes.infrastructure.models import Quote, QuoteItem
from app.modules.users.infrastructure.models import User
from app.shared.pagination import PageParams, paginate


class QuoteRepository(Protocol):
    def list_quotes(self, filters: dict, params: PageParams, user: User) -> tuple[list[Quote], int]: ...
    def get_quote(self, public_id: UUID) -> Quote | None: ...
    def add(self, quote: Quote) -> None: ...
    def delete(self, quote: Quote) -> None: ...
    def get_prospect_id(self, public_id: UUID) -> int | None: ...
    def get_opportunity_id(self, public_id: UUID) -> int | None: ...
    def get_product_id(self, public_id: UUID) -> int | None: ...
    def get_user_id(self, public_id: UUID) -> int | None: ...


class SqlQuoteRepository:
    def __init__(self, session: Session) -> None:
        self.s = session

    def _base_query(self) -> select:
        return (
            select(Quote)
            .where(Quote.deleted_at.is_(None))
            .options(
                selectinload(Quote.prospect),
                selectinload(Quote.opportunity),
                selectinload(Quote.items).selectinload(QuoteItem.product),
            )
        )

    def list_quotes(self, filters: dict, params: PageParams, user: User) -> tuple[list[Quote], int]:
        from app.modules.rbac.domain.permissions import P

        stmt = self._base_query()
        if P.PROSPECTS_READ_ALL not in user.permission_codes:
            stmt = stmt.where(Quote.prospect.has(Prospect.owner_id == user.id))
        if filters.get("status"):
            stmt = stmt.where(Quote.status == filters["status"])
        if filters.get("prospect_id"):
            stmt = stmt.where(Quote.prospect_id == filters["prospect_id"])
        if filters.get("opportunity_id"):
            stmt = stmt.where(Quote.opportunity_id == filters["opportunity_id"])
        stmt = stmt.order_by(Quote.created_at.desc())
        return paginate(self.s, stmt, params)

    def get_quote(self, public_id: UUID) -> Quote | None:
        return self.s.scalar(self._base_query().where(Quote.public_id == public_id))

    def add(self, quote: Quote) -> None:
        self.s.add(quote)
        self.s.flush()

    def delete(self, quote: Quote) -> None:
        quote.deleted_at = func.now()

    def get_prospect_id(self, public_id: UUID) -> int | None:
        return self.s.scalar(select(Prospect.id).where(Prospect.public_id == public_id))

    def get_opportunity_id(self, public_id: UUID) -> int | None:
        from app.modules.opportunities.infrastructure.models import Opportunity

        return self.s.scalar(select(Opportunity.id).where(Opportunity.public_id == public_id))

    def get_product_id(self, public_id: UUID) -> int | None:
        return self.s.scalar(select(Product.id).where(Product.public_id == public_id))

    def get_user_id(self, public_id: UUID) -> int | None:
        return self.s.scalar(select(User.id).where(User.public_id == public_id))
