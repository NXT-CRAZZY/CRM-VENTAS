from typing import Protocol
from uuid import UUID

from sqlalchemy import exists, func, or_, select
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
    def opportunity_prospect_id(self, opportunity_id: int) -> int | None: ...
    def get_product_id(self, public_id: UUID) -> int | None: ...
    def get_opportunity(self, opportunity_id: int): ...
    def open_opportunities_of_prospect(self, prospect_id: int) -> list: ...
    def catalog_id_by_code(self, catalog_code: str, option_code: str) -> int | None: ...
    def catalog_id_by_public(self, catalog_code: str, public_id: UUID) -> int | None: ...
    def sibling_quotes(self, opportunity_id: int, exclude_id: int) -> list[Quote]: ...
    def pending_tasks(self, quote_ids: list[int]) -> list: ...
    def add_task(self, task) -> None: ...
    def add_opportunity_refresh(self, opportunity) -> None: ...
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
            stmt = stmt.where(
                Quote.prospect_id
                == select(Prospect.id).where(Prospect.public_id == filters["prospect_id"]).scalar_subquery()
            )
        if filters.get("opportunity_id"):
            stmt = stmt.where(Quote.opportunity_id == filters["opportunity_id"])
        if filters.get("search"):
            like = f"%{filters['search'].strip()}%"
            stmt = stmt.where(
                Quote.prospect.has(
                    or_(
                        Prospect.display_name.ilike(like),
                        Prospect.trade_name.ilike(like),
                        Prospect.document_number.ilike(like),
                    )
                )
            )
        if filters.get("date_from"):
            stmt = stmt.where(Quote.issue_date >= filters["date_from"])
        if filters.get("date_to"):
            stmt = stmt.where(Quote.issue_date <= filters["date_to"])
        if filters.get("owner_id") and P.PROSPECTS_READ_ALL in user.permission_codes:
            owner = self.get_user_id(filters["owner_id"])
            stmt = stmt.where(Quote.prospect.has(Prospect.owner_id == (owner if owner is not None else -1)))
        if filters.get("product_id"):
            product = self.get_product_id(filters["product_id"])
            stmt = stmt.where(
                exists().where(
                    QuoteItem.quote_id == Quote.id,
                    QuoteItem.product_id == (product if product is not None else -1),
                )
            )

        sort = filters.get("sort", "newest")
        if sort == "oldest":
            stmt = stmt.order_by(Quote.issue_date.asc(), Quote.created_at.asc())
        elif sort == "amount_desc":
            stmt = stmt.order_by(Quote.total.desc(), Quote.created_at.desc())
        elif sort == "amount_asc":
            stmt = stmt.order_by(Quote.total.asc(), Quote.created_at.desc())
        elif sort == "expiring":
            stmt = stmt.where(Quote.status == "SENT", Quote.expiration_date.is_not(None)).order_by(
                Quote.expiration_date.asc()
            )
        else:
            stmt = stmt.order_by(Quote.issue_date.desc(), Quote.created_at.desc())
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

    def opportunity_prospect_id(self, opportunity_id: int) -> int | None:
        from app.modules.opportunities.infrastructure.models import Opportunity

        return self.s.scalar(select(Opportunity.prospect_id).where(Opportunity.id == opportunity_id))

    def get_opportunity(self, opportunity_id: int):
        from app.modules.opportunities.infrastructure.models import Opportunity

        return self.s.get(Opportunity, opportunity_id)

    def open_opportunities_of_prospect(self, prospect_id: int) -> list:
        from app.modules.opportunities.infrastructure.models import Opportunity

        stmt = (
            select(Opportunity)
            .where(
                Opportunity.prospect_id == prospect_id,
                Opportunity.deleted_at.is_(None),
                Opportunity.stage.has(CatalogOption.code.not_in(["CERRADO_GANADO", "CERRADO_PERDIDO"])),
            )
            .order_by(Opportunity.created_at.desc())
        )
        return list(self.s.scalars(stmt).unique().all())

    def catalog_id_by_code(self, catalog_code: str, option_code: str) -> int | None:
        from app.modules.catalogs.infrastructure.models import Catalog

        return self.s.scalar(
            select(CatalogOption.id)
            .join(Catalog, Catalog.id == CatalogOption.catalog_id)
            .where(Catalog.code == catalog_code, CatalogOption.code == option_code)
        )

    def catalog_id_by_public(self, catalog_code: str, public_id: UUID) -> int | None:
        from app.modules.catalogs.infrastructure.models import Catalog

        return self.s.scalar(
            select(CatalogOption.id)
            .join(Catalog, Catalog.id == CatalogOption.catalog_id)
            .where(Catalog.code == catalog_code, CatalogOption.public_id == public_id)
        )

    def sibling_quotes(self, opportunity_id: int, exclude_id: int) -> list[Quote]:
        stmt = self._base_query().where(Quote.opportunity_id == opportunity_id, Quote.id != exclude_id)
        return list(self.s.scalars(stmt).unique().all())

    def pending_tasks(self, quote_ids: list[int]) -> list:
        from app.modules.tasks.infrastructure.models import Task

        if not quote_ids:
            return []
        stmt = select(Task).where(
            Task.quote_id.in_(quote_ids), Task.status == "PENDING", Task.deleted_at.is_(None)
        )
        return list(self.s.scalars(stmt).unique().all())

    def add_task(self, task) -> None:
        self.s.add(task)
        self.s.flush()

    def add_opportunity_refresh(self, opportunity) -> None:
        self.s.flush()
        self.s.refresh(opportunity)

    def get_product_id(self, public_id: UUID) -> int | None:
        return self.s.scalar(select(Product.id).where(Product.public_id == public_id))

    def get_user_id(self, public_id: UUID) -> int | None:
        return self.s.scalar(select(User.id).where(User.public_id == public_id))
