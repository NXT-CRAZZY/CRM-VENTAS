from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base, IdMixin, TimestampMixin


class ImportJob(IdMixin, TimestampMixin, Base):
    __tablename__ = "import_jobs"
    __table_args__ = (Index("ix_import_jobs_created_by_status", "created_by_id", "status"),)

    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    sheet_name: Mapped[str | None] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(30), default="PENDING", nullable=False, index=True)

    total_rows: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    processed_rows: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_prospects: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    updated_prospects: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_interactions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_opportunities: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    errors: Mapped[list["ImportRowError"]] = relationship(
        "ImportRowError", lazy="selectin", cascade="all, delete-orphan", order_by="ImportRowError.row_number"
    )

    created_by_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), index=True, nullable=True
    )
    created_by: Mapped["User"] = relationship("User", lazy="joined")


class ImportRowError(IdMixin, TimestampMixin, Base):
    __tablename__ = "import_row_errors"

    import_job_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("import_jobs.id", ondelete="CASCADE"), index=True, nullable=False
    )
    row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    raw_data: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    field: Mapped[str | None] = mapped_column(String(60))
    message: Mapped[str] = mapped_column(Text, nullable=False)
