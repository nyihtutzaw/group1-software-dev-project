"""F5 Security & auditability — database tables."""

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, TimestampMixin


class LedgerEntry(TimestampMixin, Base):
    """An immutable, append-only, hash-chained record of a critical action (FR-07, FR-09)."""

    __tablename__ = "ledger_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    actor_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    entity: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    entity_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    prev_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
