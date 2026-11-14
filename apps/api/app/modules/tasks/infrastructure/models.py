from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base, IdMixin, TimestampMixin


class Task(IdMixin, TimestampMixin, Base):
    __tablename__ = "tasks"
    __table_args__ = (
        Index("ix_tasks_assignee_status_due", "assignee_id", "status", "due_at"),
        Index("ix_tasks_prospect_status", "prospect_id", "status"),
        Index("ix_tasks_due_at", "due_at"),
    )

    prospect_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("prospects.id", ondelete="CASCADE"), index=True, nullable=False
    )
    opportunity_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("opportunities.id", ondelete="SET NULL"), index=True, nullable=True
    )
    quote_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("quotes.id", ondelete="SET NULL"), index=True, nullable=True
    )
    interaction_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("interactions.id", ondelete="SET NULL"), index=True, nullable=True
    )
    assignee_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), index=True, nullable=True
    )
    type_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("catalog_options.id", ondelete="RESTRICT"), index=True, nullable=True
    )
    priority_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("catalog_options.id", ondelete="RESTRICT"), index=True, nullable=True
    )

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    remind_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    status: Mapped[str] = mapped_column(String(20), default="PENDING", nullable=False, index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)

    prospect: Mapped["Prospect"] = relationship("Prospect", lazy="joined")
    opportunity: Mapped["Opportunity | None"] = relationship("Opportunity", lazy="joined")
    assignee: Mapped["User | None"] = relationship("User", lazy="joined")
    type: Mapped["CatalogOption | None"] = relationship("CatalogOption", foreign_keys=[type_id], lazy="joined")
    priority: Mapped["CatalogOption | None"] = relationship("CatalogOption", foreign_keys=[priority_id], lazy="joined")
