from typing import Protocol
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.modules.prospects.domain.enums import PersonType
from app.modules.prospects.infrastructure.models import Prospect, ProspectAssignment, ProspectStatusHistory, Tag
from app.modules.prospects.schemas import DuplicateCheckRequest, ProspectFilters
from app.modules.users.infrastructure.models import User
from app.shared.pagination import PageParams, paginate


class ProspectRepository(Protocol):
    def list_prospects(self, filters: ProspectFilters, params: PageParams, accessible_user_ids: list[int] | None) -> tuple[list[Prospect], int]: ...
    def get_prospect(self, public_id: UUID) -> Prospect | None: ...
    def get_prospect_assignments(self, public_id: UUID) -> list[ProspectAssignment]: ...
    def get_prospect_status_history(self, public_id: UUID) -> list[ProspectStatusHistory]: ...
    def get_prospect_by_document(self, document_type_id: int, document_number: str) -> Prospect | None: ...
    def find_duplicates(self, request: DuplicateCheckRequest, exclude_public_id: UUID | None) -> list[dict]: ...
    def next_code(self) -> str: ...
    def add_prospect(self, prospect: Prospect) -> None: ...
    def add_assignment(self, assignment: ProspectAssignment) -> None: ...
    def add_status_history(self, history: ProspectStatusHistory) -> None: ...
    def get_tag(self, public_id: UUID) -> Tag | None: ...
    def get_tags_by_public_ids(self, ids: list[UUID]) -> list[Tag]: ...
    def get_user_id(self, public_id: UUID) -> int | None: ...
    def get_catalog_option_id(self, public_id: UUID) -> int | None: ...
    def get_catalog_option_id_by_code(self, catalog_code: str, option_code: str) -> int | None: ...


class SqlProspectRepository:
    def __init__(self, session: Session) -> None:
        self.s = session

    def _base_query(self) -> select:
        return (
            select(Prospect)
            .where(Prospect.deleted_at.is_(None))
            .options(
                joinedload(Prospect.owner),
                selectinload(Prospect.tags),
            )
        )

    def list_prospects(
        self,
        filters: ProspectFilters,
        params: PageParams,
        accessible_user_ids: list[int] | None,
    ) -> tuple[list[Prospect], int]:
        stmt = self._base_query()
        if accessible_user_ids is not None:
            stmt = stmt.where(Prospect.owner_id.in_(accessible_user_ids))
        if filters.person_type:
            stmt = stmt.where(Prospect.person_type == filters.person_type)
        if filters.status:
            stmt = stmt.where(Prospect.status == filters.status)
        if filters.relationship_type:
            stmt = stmt.where(Prospect.relationship_type == filters.relationship_type)
        if filters.owner_id:
            owner_id = self.get_user_id(filters.owner_id)
            if owner_id:
                stmt = stmt.where(Prospect.owner_id == owner_id)
        if filters.interest_level_id:
            iid = self.get_catalog_option_id(filters.interest_level_id)
            if iid:
                stmt = stmt.where(Prospect.interest_level_id == iid)
        if filters.priority_id:
            pid = self.get_catalog_option_id(filters.priority_id)
            if pid:
                stmt = stmt.where(Prospect.priority_id == pid)
        if filters.source_id:
            sid = self.get_catalog_option_id(filters.source_id)
            if sid:
                stmt = stmt.where(Prospect.source_id == sid)
        if filters.tag_ids:
            tag_internal_ids = [t.id for t in self.get_tags_by_public_ids(filters.tag_ids)]
            if tag_internal_ids:
                stmt = stmt.where(Prospect.tags.any(Tag.id.in_(tag_internal_ids)))
        if filters.q:
            q = filters.q.strip()
            like = f"%{q}%"
            stmt = stmt.where(
                or_(
                    Prospect.display_name.ilike(like),
                    Prospect.trade_name.ilike(like),
                    Prospect.email.ilike(like),
                    Prospect.phone.ilike(like),
                    Prospect.document_number.ilike(like),
                    Prospect.code.ilike(like),
                )
            )
        stmt = stmt.order_by(Prospect.created_at.desc())
        return paginate(self.s, stmt, params)

    def get_prospect(self, public_id: UUID) -> Prospect | None:
        return self.s.scalar(
            self._base_query()
            .where(Prospect.public_id == public_id)
            .options(
                selectinload(Prospect.contacts),
            )
        )

    def get_prospect_assignments(self, public_id: UUID) -> list[ProspectAssignment]:
        return list(
            self.s.scalars(
                select(ProspectAssignment)
                .join(Prospect, Prospect.id == ProspectAssignment.prospect_id)
                .where(Prospect.public_id == public_id)
                .options(selectinload(ProspectAssignment.from_user), selectinload(ProspectAssignment.to_user), selectinload(ProspectAssignment.assigned_by))
                .order_by(ProspectAssignment.assigned_at.desc())
            )
        )

    def get_prospect_status_history(self, public_id: UUID) -> list[ProspectStatusHistory]:
        return list(
            self.s.scalars(
                select(ProspectStatusHistory)
                .join(Prospect, Prospect.id == ProspectStatusHistory.prospect_id)
                .where(Prospect.public_id == public_id)
                .options(selectinload(ProspectStatusHistory.changed_by))
                .order_by(ProspectStatusHistory.created_at.desc())
            )
        )

    def get_prospect_by_document(self, document_type_id: int, document_number: str) -> Prospect | None:
        return self.s.scalar(
            self._base_query().where(
                Prospect.document_type_id == document_type_id,
                Prospect.document_number == document_number,
            )
        )

    def find_duplicates(self, request: DuplicateCheckRequest, exclude_public_id: UUID | None) -> list[dict]:
        matches: list[dict] = []
        stmt = self._base_query()
        if exclude_public_id:
            stmt = stmt.where(Prospect.public_id != exclude_public_id)

        if request.document_number:
            doc_type_id = None
            if request.document_type_id:
                doc_type_id = self.get_catalog_option_id(request.document_type_id)
            elif request.person_type:
                inferred = "RUC" if request.person_type == PersonType.JURIDICA else "DNI"
                doc_type_id = self.get_catalog_option_id_by_code("document_type", inferred)
            if doc_type_id:
                exact = self.s.scalar(
                    stmt.where(
                        Prospect.document_type_id == doc_type_id,
                        Prospect.document_number == request.document_number,
                    )
                )
                if exact:
                    matches.append({"prospect": exact, "field": "documento", "type": "exact"})

        if request.email:
            email_match = self.s.scalar(stmt.where(Prospect.email.ilike(request.email.strip())))
            if email_match:
                matches.append({"prospect": email_match, "field": "email", "type": "exact"})

        if request.phone:
            phone = request.phone.strip()
            phone_match = self.s.scalar(stmt.where(Prospect.phone.ilike(phone)))
            if phone_match:
                matches.append({"prospect": phone_match, "field": "teléfono", "type": "exact"})

        return matches

    def next_code(self) -> str:
        current = self.s.scalar(select(func.max(Prospect.id)))
        return f"PRO-{((current or 0) + 1):06d}"

    def add_prospect(self, prospect: Prospect) -> None:
        self.s.add(prospect)
        self.s.flush()

    def add_assignment(self, assignment: ProspectAssignment) -> None:
        self.s.add(assignment)

    def add_status_history(self, history: ProspectStatusHistory) -> None:
        self.s.add(history)

    def get_tag(self, public_id: UUID) -> Tag | None:
        return self.s.scalar(select(Tag).where(Tag.public_id == public_id))

    def get_tags_by_public_ids(self, ids: list[UUID]) -> list[Tag]:
        if not ids:
            return []
        return list(self.s.scalars(select(Tag).where(Tag.public_id.in_(ids))))

    def get_user_id(self, public_id: UUID) -> int | None:
        from app.modules.users.infrastructure.models import User

        return self.s.scalar(select(User.id).where(User.public_id == public_id))

    def get_catalog_option_id(self, public_id: UUID) -> int | None:
        from app.modules.catalogs.infrastructure.models import CatalogOption

        return self.s.scalar(select(CatalogOption.id).where(CatalogOption.public_id == public_id))

    def get_catalog_option_id_by_code(self, catalog_code: str, option_code: str) -> int | None:
        from app.modules.catalogs.infrastructure.models import Catalog, CatalogOption

        return self.s.scalar(
            select(CatalogOption.id)
            .join(Catalog, Catalog.id == CatalogOption.catalog_id)
            .where(Catalog.code == catalog_code, CatalogOption.code == option_code)
        )
