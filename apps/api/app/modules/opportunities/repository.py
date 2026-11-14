from typing import Protocol
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.modules.catalogs.infrastructure.models import Catalog, CatalogOption
from app.modules.opportunities.infrastructure.models import Opportunity
from app.modules.users.infrastructure.models import User
from app.shared.pagination import PageParams, paginate


class OpportunityRepository(Protocol):
    def list_opportunities(
        self, filters: dict, params: PageParams, user: User
    ) -> tuple[list[Opportunity], int]: ...
    def get_opportunity(self, public_id: UUID) -> Opportunity | None: ...
    def add(self, opportunity: Opportunity) -> None: ...
    def delete(self, opportunity: Opportunity) -> None: ...
    def flush(self) -> None: ...
    def refresh(self, opportunity: Opportunity) -> None: ...
    def get_prospect_id(self, public_id: UUID) -> int | None: ...
    def get_user_id(self, public_id: UUID) -> int | None: ...
    def get_prospect_relationship(self, prospect_id: int) -> str | None: ...
    def get_catalog_option_id(self, public_id: UUID) -> int | None: ...
    def get_catalog_option_id_by_code(self, catalog_code: str, option_code: str) -> int | None: ...
    def list_open_for_prospect(self, prospect_id: int) -> list[Opportunity]: ...
    def get_latest_for_prospect(self, prospect_id: int) -> Opportunity | None: ...
    def reopen_accepted_quotes(self, opportunity_id: int) -> None: ...


class SqlOpportunityRepository:
    def __init__(self, session: Session) -> None:
        self.s = session

    def _base_query(self) -> select:
        return (
            select(Opportunity)
            .where(Opportunity.deleted_at.is_(None))
            .options(
                selectinload(Opportunity.owner),
                selectinload(Opportunity.stage),
                selectinload(Opportunity.type),
                selectinload(Opportunity.loss_reason),
                selectinload(Opportunity.prospect),
            )
        )

    def list_opportunities(
        self, filters: dict, params: PageParams, user: User
    ) -> tuple[list[Opportunity], int]:
        from app.modules.rbac.domain.permissions import P

        stmt = self._base_query()
        if P.PROSPECTS_READ_ALL not in user.permission_codes:
            from app.modules.prospects.infrastructure.models import Prospect

            # Ve las suyas y las de los prospectos que atiende (aunque la oportunidad no tenga responsable).
            stmt = stmt.where(
                or_(
                    Opportunity.owner_id == user.id,
                    Opportunity.prospect_id.in_(select(Prospect.id).where(Prospect.owner_id == user.id)),
                )
            )
        if filters.get("stage_id"):
            stmt = stmt.where(Opportunity.stage_id == filters["stage_id"])
        if filters.get("owner_id"):
            stmt = stmt.where(Opportunity.owner_id == filters["owner_id"])
        if filters.get("type_id"):
            stmt = stmt.where(Opportunity.type_id == filters["type_id"])
        if filters.get("expected_close_before"):
            stmt = stmt.where(Opportunity.expected_close_date <= filters["expected_close_before"])
        if filters.get("expected_close_after"):
            stmt = stmt.where(Opportunity.expected_close_date >= filters["expected_close_after"])
        if filters.get("prospect_id"):
            from app.modules.prospects.infrastructure.models import Prospect

            stmt = stmt.where(
                Opportunity.prospect_id
                == select(Prospect.id).where(Prospect.public_id == filters["prospect_id"]).scalar_subquery()
            )
        stmt = stmt.order_by(Opportunity.created_at.desc())
        return paginate(self.s, stmt, params)

    def get_opportunity(self, public_id: UUID) -> Opportunity | None:
        return self.s.scalar(self._base_query().where(Opportunity.public_id == public_id))

    def add(self, opportunity: Opportunity) -> None:
        self.s.add(opportunity)
        self.s.flush()

    def delete(self, opportunity: Opportunity) -> None:
        opportunity.deleted_at = func.now()

    def flush(self) -> None:
        self.s.flush()

    def refresh(self, opportunity: Opportunity) -> None:
        self.s.refresh(opportunity)

    def get_prospect_id(self, public_id: UUID) -> int | None:
        from app.modules.prospects.infrastructure.models import Prospect

        return self.s.scalar(select(Prospect.id).where(Prospect.public_id == public_id))

    def get_prospect_relationship(self, prospect_id: int) -> str | None:
        from app.modules.prospects.infrastructure.models import Prospect

        return self.s.scalar(select(Prospect.relationship_type).where(Prospect.id == prospect_id))

    def get_user_id(self, public_id: UUID) -> int | None:
        return self.s.scalar(select(User.id).where(User.public_id == public_id))

    def get_catalog_option_id(self, public_id: UUID) -> int | None:
        return self.s.scalar(select(CatalogOption.id).where(CatalogOption.public_id == public_id))

    def get_catalog_option_id_by_code(self, catalog_code: str, option_code: str) -> int | None:
        return self.s.scalar(
            select(CatalogOption.id)
            .join(Catalog, Catalog.id == CatalogOption.catalog_id)
            .where(Catalog.code == catalog_code, CatalogOption.code == option_code)
        )

    def list_open_for_prospect(self, prospect_id: int) -> list[Opportunity]:
        """Oportunidades del prospecto que aún no están cerradas (la más reciente primero)."""
        return list(
            self.s.scalars(
                self._base_query()
                .join(CatalogOption, CatalogOption.id == Opportunity.stage_id)
                .where(
                    Opportunity.prospect_id == prospect_id,
                    CatalogOption.code.not_in(("CERRADO_GANADO", "CERRADO_PERDIDO")),
                )
                .order_by(Opportunity.created_at.desc(), Opportunity.id.desc())
            ).unique()
        )

    def reopen_accepted_quotes(self, opportunity_id: int) -> None:
        from app.modules.quotes.infrastructure.models import Quote

        quotes = self.s.scalars(
            select(Quote).where(
                Quote.opportunity_id == opportunity_id, Quote.status == "ACCEPTED", Quote.deleted_at.is_(None)
            )
        ).unique().all()
        for q in quotes:
            q.status = "SENT"
            q.accepted_at = None

    def get_latest_for_prospect(self, prospect_id: int) -> Opportunity | None:
        """Oportunidad más reciente del prospecto (abierta o cerrada)."""
        return self.s.scalar(
            self._base_query()
            .where(Opportunity.prospect_id == prospect_id)
            .order_by(Opportunity.created_at.desc(), Opportunity.id.desc())
            .limit(1)
        )
