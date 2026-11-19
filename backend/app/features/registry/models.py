"""F4 publication records; source project, approval and ledger remain owned by F1/F3/F5."""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    false,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class RegistryCredit(Base):
    __tablename__ = "registry_credits"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_registry_quantity"),
        CheckConstraint("vintage BETWEEN 1900 AND 2200", name="ck_registry_vintage"),
        CheckConstraint(
            "status IN ('active', 'retired', 'revoked', 'buffer')", name="ck_registry_status"
        ),
        # One tradable batch and one buffer batch may share an approval. NULL approvals
        # (demo rows) are not treated as equal, so several of those can stay 'active'.
        UniqueConstraint(
            "source_approval_id", "status", name="uq_registry_credits_approval_status"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    # Source links are internal; F3 owns approval and F4 reuses this row as its issued batch.
    source_project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id"), index=True)
    source_approval_id: Mapped[int | None] = mapped_column(ForeignKey("approvals.id"))
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    serial: Mapped[str] = mapped_column(String(120), unique=True)
    project_reference: Mapped[str] = mapped_column(String(80), index=True)
    project_name: Mapped[str] = mapped_column(String(200))
    country: Mapped[str] = mapped_column(String(100))
    methodology: Mapped[str] = mapped_column(String(200))
    vintage: Mapped[int]
    quantity: Mapped[int]
    status: Mapped[str] = mapped_column(String(16), default="active")
    verifier_name: Mapped[str] = mapped_column(String(160))
    verification_reference: Mapped[str] = mapped_column(String(80))
    approval_reference: Mapped[str] = mapped_column(String(80))
    signed_off_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    snapshot_sha256: Mapped[str] = mapped_column(String(64))
    # Internal fields are deliberately excluded from every public/buyer schema.
    developer_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    published_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"))


class RegistryEvidence(Base):
    """Only reviewed buyer-safe summaries, never original uploads or storage paths."""

    __tablename__ = "registry_evidence"
    id: Mapped[int] = mapped_column(primary_key=True)
    credit_id: Mapped[int] = mapped_column(ForeignKey("registry_credits.id"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    summary: Mapped[str] = mapped_column(Text)
    source_reference: Mapped[str] = mapped_column(String(200))
    buyer_visible: Mapped[bool] = mapped_column(default=False)


class RegistryProjectAccess(Base):
    __tablename__ = "registry_project_access"
    project_reference: Mapped[str] = mapped_column(String(80), primary_key=True)
    buyer_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)


class RegistryCreditEvent(Base):
    __tablename__ = "registry_credit_events"
    __table_args__ = (
        CheckConstraint(
            "action IN ('issued', 'retired', 'revoked')", name="ck_registry_event_action"
        ),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    credit_id: Mapped[int] = mapped_column(ForeignKey("registry_credits.id"), index=True)
    action: Mapped[str] = mapped_column(String(16))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class RegistryHolding(Base):
    """A contiguous unit range of one issued batch held by a buyer (#44).

    Staff allocate ranges from the batch's unallocated tail; a buyer retires all or part of a
    held range, which splits it. Retired rows are permanently locked by a database trigger
    (no update or delete), so retired credits can never be transferred, resold or unretired.
    """

    __tablename__ = "registry_holdings"
    __table_args__ = (
        CheckConstraint("first_unit >= 1", name="ck_registry_holding_first_unit"),
        CheckConstraint("last_unit >= first_unit", name="ck_registry_holding_range"),
        CheckConstraint("status IN ('held', 'retired')", name="ck_registry_holding_status"),
        CheckConstraint(
            "(status = 'held' AND retired_at IS NULL AND beneficiary IS NULL"
            " AND reason IS NULL AND reporting_year IS NULL)"
            " OR (status = 'retired' AND retired_at IS NOT NULL AND beneficiary IS NOT NULL"
            " AND reason IS NOT NULL AND reporting_year IS NOT NULL)",
            name="ck_registry_holding_retirement",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    credit_id: Mapped[int] = mapped_column(ForeignKey("registry_credits.id"), index=True)
    buyer_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    first_unit: Mapped[int]
    last_unit: Mapped[int]
    status: Mapped[str] = mapped_column(String(16), default="held")
    allocated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    allocated_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    retired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    beneficiary: Mapped[str | None] = mapped_column(String(200))
    reason: Mapped[str | None] = mapped_column(String(500))
    reporting_year: Mapped[int | None]

    @property
    def quantity(self) -> int:
        return self.last_unit - self.first_unit + 1
