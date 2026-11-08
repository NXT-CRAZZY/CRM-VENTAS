from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base, IdMixin, TimestampMixin


class Tag(IdMixin, TimestampMixin, Base):
    __tablename__ = "tags"

    name: Mapped[str] = mapped_column(String(60), unique=True, nullable=False)
    color: Mapped[str | None] = mapped_column(String(9))
    description: Mapped[str | None] = mapped_column(Text)


class Prospect(IdMixin, TimestampMixin, Base):
    __tablename__ = "prospects"
    __table_args__ = (
        CheckConstraint(
            "person_type IN ('NATURAL','JURIDICA')",
            name="ck_prospects_person_type",
        ),
        CheckConstraint(
            "relationship_type IN ('PROSPECTO','CLIENTE')",
            name="ck_prospects_relationship_type",
        ),
        CheckConstraint(
            "status IN ('ACTIVO','EN_PAUSA','DESCARTADO','NO_CALIFICA','INACTIVO')",
            name="ck_prospects_status",
        ),
        CheckConstraint(
            "(person_type = 'NATURAL' AND first_name IS NOT NULL AND last_name IS NOT NULL) OR "
            "(person_type = 'JURIDICA' AND legal_name IS NOT NULL)",
            name="ck_prospects_names_by_type",
        ),
        UniqueConstraint(
            "document_type_id",
            "document_number",
            name="uq_prospects_document",
        ),
        Index("ix_prospects_owner_status", "owner_id", "status"),
        Index("ix_prospects_next_action", "next_action_at"),
        Index("ix_prospects_display_name_trgm", "display_name"),
        Index("ix_prospects_trade_name_trgm", "trade_name"),
        Index("ix_prospects_email", "email"),
        Index("ix_prospects_phone", "phone"),
    )

    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    person_type: Mapped[str] = mapped_column(String(20), nullable=False)

    document_type_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("catalog_options.id", ondelete="RESTRICT"), index=True, nullable=True
    )
    document_number: Mapped[str | None] = mapped_column(String(20), index=True, nullable=True)

    # Persona natural
    first_name: Mapped[str | None] = mapped_column(String(100))
    last_name: Mapped[str | None] = mapped_column(String(100))
    birth_date: Mapped[date | None] = mapped_column(Date)

    # Persona jurídica
    legal_name: Mapped[str | None] = mapped_column(String(200))
    trade_name: Mapped[str | None] = mapped_column(String(200))

    display_name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)

    email: Mapped[str | None] = mapped_column(String(120))
    phone: Mapped[str | None] = mapped_column(String(30))
    phone_alt: Mapped[str | None] = mapped_column(String(30))
    whatsapp: Mapped[str | None] = mapped_column(String(30))
    address: Mapped[str | None] = mapped_column(Text)

    source_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("catalog_options.id", ondelete="RESTRICT"), index=True
    )
    acquisition_channel_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("catalog_options.id", ondelete="RESTRICT"), index=True
    )
    interest_level_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("catalog_options.id", ondelete="RESTRICT"), index=True
    )
    priority_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("catalog_options.id", ondelete="RESTRICT"), index=True
    )
    discard_reason_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("catalog_options.id", ondelete="RESTRICT"), index=True
    )

    relationship_type: Mapped[str] = mapped_column(String(20), default="PROSPECTO", nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), default="ACTIVO", nullable=False, index=True)

    converted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    converted_by_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"))

    owner_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="RESTRICT"), index=True, nullable=False
    )

    # Campos desnormalizados para listados/alertas
    first_contact_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_contact_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_action_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_action_desc: Mapped[str | None] = mapped_column(String(200))
    interaction_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_result_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("catalog_options.id", ondelete="SET NULL"), index=True
    )
    score: Mapped[Decimal] = mapped_column(Numeric(8, 2), default=Decimal("0"), nullable=False)
    score_breakdown: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)

    notes: Mapped[str | None] = mapped_column(Text)
    legacy_source: Mapped[str | None] = mapped_column(String(100))
    legacy_row: Mapped[int | None] = mapped_column(Integer)
    legacy_code: Mapped[str | None] = mapped_column(String(40))
    legacy_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)

    owner: Mapped["User"] = relationship("User", foreign_keys=[owner_id], lazy="joined")
    document_type: Mapped["CatalogOption"] = relationship(
        "CatalogOption", foreign_keys=[document_type_id], lazy="joined"
    )
    source: Mapped["CatalogOption"] = relationship("CatalogOption", foreign_keys=[source_id], lazy="joined")
    acquisition_channel: Mapped["CatalogOption"] = relationship(
        "CatalogOption", foreign_keys=[acquisition_channel_id], lazy="joined"
    )
    interest_level: Mapped["CatalogOption"] = relationship(
        "CatalogOption", foreign_keys=[interest_level_id], lazy="joined"
    )
    priority: Mapped["CatalogOption"] = relationship("CatalogOption", foreign_keys=[priority_id], lazy="joined")
    discard_reason: Mapped["CatalogOption"] = relationship(
        "CatalogOption", foreign_keys=[discard_reason_id], lazy="joined"
    )
    last_result: Mapped["CatalogOption"] = relationship("CatalogOption", foreign_keys=[last_result_id], lazy="joined")
    converted_by: Mapped["User"] = relationship("User", foreign_keys=[converted_by_id], lazy="joined")
    tags: Mapped[list["Tag"]] = relationship(
        "Tag", secondary="prospect_tags", lazy="selectin", back_populates="prospects"
    )

    @property
    def is_active_commercially(self) -> bool:
        return self.status == "ACTIVO" and self.deleted_at is None


class ProspectContact(IdMixin, TimestampMixin, Base):
    __tablename__ = "prospect_contacts"

    prospect_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("prospects.id", ondelete="CASCADE"), index=True, nullable=False
    )
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    position: Mapped[str | None] = mapped_column(String(100))
    area: Mapped[str | None] = mapped_column(String(100))
    email: Mapped[str | None] = mapped_column(String(120))
    phone: Mapped[str | None] = mapped_column(String(30))
    whatsapp: Mapped[str | None] = mapped_column(String(30))
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)

    prospect: Mapped[Prospect] = relationship("Prospect", back_populates="contacts")


Prospect.contacts = relationship(
    "ProspectContact", order_by="ProspectContact.created_at", cascade="all, delete-orphan", back_populates="prospect"
)
Tag.prospects = relationship("Prospect", secondary="prospect_tags", back_populates="tags")


class ProspectTag(Base):
    __tablename__ = "prospect_tags"
    __table_args__ = (UniqueConstraint("prospect_id", "tag_id", name="uq_prospect_tags"),)

    prospect_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("prospects.id", ondelete="CASCADE"), primary_key=True
    )
    tag_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True)


class ProspectAssignment(IdMixin, TimestampMixin, Base):
    __tablename__ = "prospect_assignments"

    prospect_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("prospects.id", ondelete="CASCADE"), index=True, nullable=False
    )
    from_user_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"))
    to_user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    assigned_by_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"))
    reason: Mapped[str | None] = mapped_column(String(500))
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    from_user: Mapped["User"] = relationship("User", foreign_keys=[from_user_id], lazy="joined")
    to_user: Mapped["User"] = relationship("User", foreign_keys=[to_user_id], lazy="joined")
    assigned_by: Mapped["User"] = relationship("User", foreign_keys=[assigned_by_id], lazy="joined")


class ProspectStatusHistory(IdMixin, Base):
    __tablename__ = "prospect_status_history"

    prospect_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("prospects.id", ondelete="CASCADE"), index=True, nullable=False
    )
    from_relationship_type: Mapped[str | None] = mapped_column(String(20))
    to_relationship_type: Mapped[str] = mapped_column(String(20), nullable=False)
    from_status: Mapped[str | None] = mapped_column(String(20))
    to_status: Mapped[str] = mapped_column(String(20), nullable=False)
    changed_by_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"))
    reason: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    changed_by: Mapped["User"] = relationship("User", foreign_keys=[changed_by_id], lazy="joined")
