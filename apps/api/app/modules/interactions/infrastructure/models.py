from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base, IdMixin, TimestampMixin


class Interaction(IdMixin, TimestampMixin, Base):
    __tablename__ = "interactions"
    __table_args__ = (
        Index("ix_interactions_prospect_occurred", "prospect_id", "occurred_at"),
        Index("ix_interactions_next_action", "next_action_at"),
    )

    prospect_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("prospects.id", ondelete="CASCADE"), index=True, nullable=False
    )
    user_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), index=True, nullable=True
    )
    contact_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("prospect_contacts.id", ondelete="SET NULL"), index=True, nullable=True
    )

    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    channel_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("catalog_options.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    mode_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("catalog_options.id", ondelete="RESTRICT"), index=True, nullable=True
    )
    result_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("catalog_options.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    opportunity_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("opportunities.id", ondelete="SET NULL"), index=True, nullable=True
    )
    interest_level_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("catalog_options.id", ondelete="RESTRICT"), index=True, nullable=True
    )

    attempt_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    next_action_desc: Mapped[str | None] = mapped_column(String(200))
    next_action_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    stage_before: Mapped[str | None] = mapped_column(String(20))
    stage_after: Mapped[str] = mapped_column(String(20), nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)

    prospect: Mapped["Prospect"] = relationship("Prospect", lazy="joined")
    user: Mapped["User"] = relationship("User", lazy="joined")
    contact: Mapped["ProspectContact"] = relationship("ProspectContact", lazy="joined")
    channel: Mapped["CatalogOption"] = relationship("CatalogOption", foreign_keys=[channel_id], lazy="joined")
    mode: Mapped["CatalogOption"] = relationship("CatalogOption", foreign_keys=[mode_id], lazy="joined")
    result: Mapped["CatalogOption"] = relationship("CatalogOption", foreign_keys=[result_id], lazy="joined")
    interest_level: Mapped["CatalogOption"] = relationship("CatalogOption", foreign_keys=[interest_level_id], lazy="joined")
    # Oportunidad que esta interacción creó o movió de etapa (según su resultado).
    opportunity: Mapped["Opportunity | None"] = relationship("Opportunity", lazy="joined")
    # "Próxima acción" de la interacción: tarea vinculada (no eliminada), a lo sumo una.
    follow_up_task: Mapped["Task | None"] = relationship(
        "Task",
        primaryjoin="and_(Task.interaction_id == Interaction.id, Task.deleted_at.is_(None))",
        foreign_keys="Task.interaction_id",
        uselist=False,
        viewonly=True,
        lazy="selectin",
    )
