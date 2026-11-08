from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base, IdMixin, TimestampMixin
from app.modules.prospects.infrastructure.models import Prospect
from app.modules.users.infrastructure.models import User


class Alert(IdMixin, TimestampMixin, Base):
    __tablename__ = "alerts"
    __table_args__ = (
        Index("ix_alerts_user_status", "user_id", "status"),
        Index("ix_alerts_user_created", "user_id", "created_at"),
        Index("ix_alerts_prospect_type", "prospect_id", "alert_type"),
        Index("ix_alerts_dismissed_at", "dismissed_at"),
    )

    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    prospect_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("prospects.id", ondelete="CASCADE"), index=True, nullable=True
    )

    alert_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), default="UNREAD", nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String(40))
    entity_id: Mapped[str | None] = mapped_column(String(40))

    extra: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)

    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    dismissed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)

    user: Mapped[User] = relationship("User", lazy="joined")
    prospect: Mapped[Prospect | None] = relationship("Prospect", lazy="joined")

    @property
    def prospect_public_id(self) -> UUID | None:
        return self.prospect.public_id if self.prospect else None

    @property
    def prospect_display_name(self) -> str | None:
        return self.prospect.display_name if self.prospect else None
