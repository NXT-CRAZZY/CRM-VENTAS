from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    ForeignKey,
    CheckConstraint,
    Index,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base, IdMixin, TimestampMixin


class Opportunity(IdMixin, TimestampMixin, Base):
    __tablename__ = "opportunities"
    __table_args__ = (
        CheckConstraint("client_status IN ('NUEVO','EXISTENTE')", name="ck_opportunities_client_status"),
        Index("ix_opportunities_prospect_stage", "prospect_id", "stage_id"),
        Index("ix_opportunities_owner_stage", "owner_id", "stage_id"),
        Index("ix_opportunities_expected_close", "expected_close_date"),
        Index("ix_opportunities_deleted_at", "deleted_at"),
    )

    prospect_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("prospects.id", ondelete="CASCADE"), index=True, nullable=False
    )
    stage_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("catalog_options.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    type_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("catalog_options.id", ondelete="RESTRICT"), index=True, nullable=True
    )
    loss_reason_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("catalog_options.id", ondelete="RESTRICT"), index=True, nullable=True
    )
    owner_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), index=True, nullable=True
    )

    # Cliente nuevo o existente al momento de crear la oportunidad (se congela, no se recalcula).
    client_status: Mapped[str] = mapped_column(String(20), default="NUEVO", server_default="NUEVO", nullable=False)

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    estimated_amount: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    probability: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    expected_close_date: Mapped[date | None] = mapped_column(Date, index=True, nullable=True)
    actual_close_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)

    prospect: Mapped["Prospect"] = relationship("Prospect", lazy="joined")
    owner: Mapped["User | None"] = relationship("User", lazy="joined")
    stage: Mapped["CatalogOption"] = relationship("CatalogOption", foreign_keys=[stage_id], lazy="joined")
    type: Mapped["CatalogOption | None"] = relationship("CatalogOption", foreign_keys=[type_id], lazy="joined")
    loss_reason: Mapped["CatalogOption | None"] = relationship(
        "CatalogOption", foreign_keys=[loss_reason_id], lazy="joined"
    )
