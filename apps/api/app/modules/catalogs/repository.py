from typing import Protocol
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.catalogs.infrastructure.models import Catalog, CatalogOption


class CatalogRepository(Protocol):
    def list_catalogs(self) -> list[tuple[Catalog, int]]: ...
    def get_catalog(self, code: str) -> Catalog | None: ...
    def list_options(self, catalog_id: int, include_inactive: bool) -> list[CatalogOption]: ...
    def options_for(self, codes: list[str]) -> dict[str, list[CatalogOption]]: ...
    def get_option(self, public_id: UUID) -> CatalogOption | None: ...
    def get_option_by_code(self, catalog_id: int, code: str) -> CatalogOption | None: ...
    def next_sort_order(self, catalog_id: int) -> int: ...
    def add(self, option: CatalogOption) -> None: ...


class SqlCatalogRepository:
    def __init__(self, session: Session) -> None:
        self.s = session

    def list_catalogs(self) -> list[tuple[Catalog, int]]:
        count = select(func.count(CatalogOption.id)).where(CatalogOption.catalog_id == Catalog.id).scalar_subquery()
        return [(c, n) for c, n in self.s.execute(select(Catalog, count).order_by(Catalog.name))]

    def get_catalog(self, code: str) -> Catalog | None:
        return self.s.scalar(select(Catalog).where(Catalog.code == code))

    def list_options(self, catalog_id: int, include_inactive: bool) -> list[CatalogOption]:
        stmt = select(CatalogOption).where(CatalogOption.catalog_id == catalog_id)
        if not include_inactive:
            stmt = stmt.where(CatalogOption.is_active.is_(True))
        return list(self.s.scalars(stmt.order_by(CatalogOption.sort_order, CatalogOption.name)))

    def options_for(self, codes: list[str]) -> dict[str, list[CatalogOption]]:
        stmt = (
            select(Catalog.code, CatalogOption)
            .join(CatalogOption, CatalogOption.catalog_id == Catalog.id)
            .where(CatalogOption.is_active.is_(True))
            .order_by(Catalog.code, CatalogOption.sort_order, CatalogOption.name)
        )
        if codes:
            stmt = stmt.where(Catalog.code.in_(codes))
        result: dict[str, list[CatalogOption]] = {}
        for code, option in self.s.execute(stmt):
            result.setdefault(code, []).append(option)
        return result

    def get_option(self, public_id: UUID) -> CatalogOption | None:
        return self.s.scalar(select(CatalogOption).where(CatalogOption.public_id == public_id))

    def get_option_by_code(self, catalog_id: int, code: str) -> CatalogOption | None:
        return self.s.scalar(
            select(CatalogOption).where(CatalogOption.catalog_id == catalog_id, CatalogOption.code == code)
        )

    def next_sort_order(self, catalog_id: int) -> int:
        current = self.s.scalar(
            select(func.max(CatalogOption.sort_order)).where(CatalogOption.catalog_id == catalog_id)
        )
        return (current or 0) + 10

    def add(self, option: CatalogOption) -> None:
        self.s.add(option)
        self.s.flush()
