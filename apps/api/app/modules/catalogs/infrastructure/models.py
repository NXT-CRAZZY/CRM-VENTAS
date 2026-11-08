from decimal import Decimal
from typing import Any

from sqlalchemy import BigInteger, Boolean, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base, IdMixin, TimestampMixin


class Catalog(IdMixin, TimestampMixin, Base):
    """Lista configurable (forma de contacto, nivel de interés, motivo de pérdida, etc.)."""

    __tablename__ = "catalogs"

    code: Mapped[str] = mapped_column(String(60), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    uses_color: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    uses_weight: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    options: Mapped[list["CatalogOption"]] = relationship(
        back_populates="catalog", order_by="CatalogOption.sort_order", cascade="all, delete-orphan"
    )


class CatalogOption(IdMixin, TimestampMixin, Base):
    __tablename__ = "catalog_options"
    __table_args__ = (UniqueConstraint("catalog_id", "code", name="uq_catalog_options_catalog_code"),)

    catalog_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("catalogs.id", ondelete="CASCADE"), index=True, nullable=False
    )
    code: Mapped[str] = mapped_column(String(40), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    color: Mapped[str | None] = mapped_column(String(9))
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    legacy_code: Mapped[str | None] = mapped_column(String(20))
    weight: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    # Opciones del sistema: el código no se puede cambiar (la lógica puede depender de él).
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    extra: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)

    catalog: Mapped[Catalog] = relationship(back_populates="options")
