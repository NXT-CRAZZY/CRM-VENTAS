from typing import Generic, TypeVar

from fastapi import Query
from pydantic import BaseModel
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

T = TypeVar("T")


class PageParams(BaseModel):
    page: int = 1
    page_size: int = 20

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


def page_params(
    page: int = Query(1, ge=1, description="Número de página (desde 1)"),
    page_size: int = Query(20, ge=1, le=100, description="Registros por página"),
) -> PageParams:
    return PageParams(page=page, page_size=page_size)


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int


def paginate(session: Session, stmt: Select, params: PageParams) -> tuple[list, int]:
    """Ejecuta el conteo y la página en el servidor; nunca carga todo el conjunto."""
    total = session.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    rows = session.scalars(stmt.limit(params.page_size).offset(params.offset)).unique().all()
    return list(rows), total
