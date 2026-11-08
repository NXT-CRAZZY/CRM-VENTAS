from decimal import Decimal

from sqlalchemy import BigInteger, Boolean, CheckConstraint, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base, IdMixin, TimestampMixin


class ProductCategory(IdMixin, TimestampMixin, Base):
    __tablename__ = "product_categories"

    code: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    product_line: Mapped[str] = mapped_column(String(40), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Product(IdMixin, TimestampMixin, Base):
    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint("list_price >= 0", name="list_price_positive"),
        CheckConstraint("kind IN ('LICENCIA_PERPETUA','SUSCRIPCION','USUARIO_ADICIONAL','DEMO')", name="kind_valid"),
        CheckConstraint("billing_period IN ('UNICO','SEMANAL','MENSUAL','ANUAL')", name="billing_period_valid"),
    )

    code: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    category_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("product_categories.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    kind: Mapped[str] = mapped_column(String(30), nullable=False)
    billing_period: Mapped[str] = mapped_column(String(20), nullable=False)
    list_price: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    legacy_code: Mapped[str | None] = mapped_column(String(20))

    category: Mapped[ProductCategory] = relationship(lazy="joined")
