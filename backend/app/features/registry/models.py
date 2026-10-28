"""F4 publication records; source project, approval and ledger remain owned by F1/F3/F5."""

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class RegistryCredit(Base):
    __tablename__ = "registry_credits"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_registry_quantity"),
        CheckConstraint("vintage BETWEEN 1900 AND 2200", name="ck_registry_vintage"),
        CheckConstraint("status IN ('active', 'retired', 'revoked')", name="ck_registry_status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
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
