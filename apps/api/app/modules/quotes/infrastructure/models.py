from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base, IdMixin, TimestampMixin


class Quote(IdMixin, TimestampMixin, Base):
    __tablename__ = "quotes"
    __table_args__ = (
        Index("ix_quotes_prospect_status", "prospect_id", "status"),
        Index("ix_quotes_opportunity_id", "opportunity_id"),
        Index("ix_quotes_deleted_at", "deleted_at"),
    )

    prospect_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("prospects.id", ondelete="CASCADE"), index=True, nullable=False
    )
    opportunity_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("opportunities.id", ondelete="SET NULL"), index=True, nullable=True
    )

    status: Mapped[str] = mapped_column(String(20), default="DRAFT", nullable=False, index=True)
    issue_date: Mapped[date] = mapped_column(Date, nullable=False)
    expiration_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    subtotal: Mapped[float] = mapped_column(Numeric(14, 2), default=0, nullable=False)
    tax: Mapped[float] = mapped_column(Numeric(14, 2), default=0, nullable=False)
    total: Mapped[float] = mapped_column(Numeric(14, 2), default=0, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)

    prospect: Mapped["Prospect"] = relationship("Prospect", lazy="joined")
    opportunity: Mapped["Opportunity | None"] = relationship("Opportunity", lazy="joined")
    items: Mapped[list["QuoteItem"]] = relationship(
        "QuoteItem", lazy="joined", cascade="all, delete-orphan", order_by="QuoteItem.id"
    )


class QuoteItem(IdMixin, TimestampMixin, Base):
    __tablename__ = "quote_items"

    quote_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("quotes.id", ondelete="CASCADE"), index=True, nullable=False
    )
    product_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("products.id", ondelete="SET NULL"), index=True, nullable=True
    )

    description: Mapped[str] = mapped_column(String(255), nullable=False)
    quantity: Mapped[int] = mapped_column(BigInteger, default=1, nullable=False)
    unit_price: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    total: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)

    product: Mapped["Product | None"] = relationship("Product", lazy="joined")
