from typing import Protocol
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.modules.catalogs.infrastructure.models import Catalog, CatalogOption
from app.modules.interactions.infrastructure.models import Interaction
from app.modules.prospects.infrastructure.models import Prospect, ProspectContact
from app.modules.users.infrastructure.models import User
from app.shared.pagination import PageParams, paginate


class InteractionRepository(Protocol):
    def list_interactions(self, prospect_public_id: UUID, params: PageParams) -> tuple[list[Interaction], int]: ...
    def get_interaction(self, prospect_public_id: UUID, public_id: UUID) -> Interaction | None: ...
    def get_interaction_by_id(self, internal_id: int) -> Interaction | None: ...
    def count_interactions(self, prospect_id: int) -> int: ...
    def latest_interaction(self, prospect_id: int) -> Interaction | None: ...
    def add(self, interaction: Interaction) -> None: ...
    def delete(self, interaction: Interaction) -> None: ...
    def get_prospect(self, public_id: UUID) -> Prospect | None: ...
    def get_prospect_id(self, public_id: UUID) -> int | None: ...
    def get_contact_id(self, public_id: UUID) -> int | None: ...
    def get_user_id(self, public_id: UUID) -> int | None: ...
    def get_catalog_option_id(self, public_id: UUID) -> int | None: ...
    def get_catalog_option_id_by_code(self, catalog_code: str, option_code: str) -> int | None: ...


class SqlInteractionRepository:
    def __init__(self, session: Session) -> None:
        self.s = session

    def _base_query(self) -> select:
        return (
            select(Interaction)
            .where(Interaction.deleted_at.is_(None))
            .options(
                selectinload(Interaction.user),
                selectinload(Interaction.contact),
                selectinload(Interaction.channel),
                selectinload(Interaction.mode),
                selectinload(Interaction.result),
                selectinload(Interaction.interest_level),
            )
        )

    def list_interactions(self, prospect_public_id: UUID, params: PageParams) -> tuple[list[Interaction], int]:
        stmt = (
            self._base_query()
            .join(Prospect, Prospect.id == Interaction.prospect_id)
            .where(Prospect.public_id == prospect_public_id)
            .order_by(Interaction.occurred_at.desc())
        )
        return paginate(self.s, stmt, params)

    def get_interaction(self, prospect_public_id: UUID, public_id: UUID) -> Interaction | None:
        return self.s.scalar(
            self._base_query()
            .join(Prospect, Prospect.id == Interaction.prospect_id)
            .where(Prospect.public_id == prospect_public_id, Interaction.public_id == public_id)
        )

    def get_interaction_by_id(self, internal_id: int) -> Interaction | None:
        return self.s.scalar(self._base_query().where(Interaction.id == internal_id))

    def count_interactions(self, prospect_id: int) -> int:
        return self.s.scalar(
            select(func.count(Interaction.id)).where(
                Interaction.prospect_id == prospect_id,
                Interaction.deleted_at.is_(None),
            )
        ) or 0

    def latest_interaction(self, prospect_id: int) -> Interaction | None:
        return self.s.scalar(
            self._base_query()
            .where(Interaction.prospect_id == prospect_id)
            .order_by(Interaction.occurred_at.desc())
            .limit(1)
        )

    def add(self, interaction: Interaction) -> None:
        self.s.add(interaction)
        self.s.flush()

    def delete(self, interaction: Interaction) -> None:
        interaction.deleted_at = func.now()

    def get_prospect(self, public_id: UUID) -> Prospect | None:
        return self.s.scalar(
            select(Prospect)
            .where(Prospect.public_id == public_id, Prospect.deleted_at.is_(None))
            .options(selectinload(Prospect.contacts))
        )

    def get_prospect_id(self, public_id: UUID) -> int | None:
        return self.s.scalar(select(Prospect.id).where(Prospect.public_id == public_id))

    def get_contact_id(self, public_id: UUID) -> int | None:
        from app.modules.prospects.infrastructure.models import ProspectContact

        return self.s.scalar(select(ProspectContact.id).where(ProspectContact.public_id == public_id))

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
