"""F1 Project registration & evidence — database tables.

`projects` started as a minimal stub added by F2; `id`, `code`, `name`, `owner_id` and
`created_at` are relied on by F2/F3/F4 — keep them. Registration fields are nullable because a
draft may be saved half-filled; `service.missing_for_submission()` decides what is complete.
"""

import enum
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, TimestampMixin


class ProjectStatus(enum.StrEnum):
    DRAFT = "draft"  # being filled in by the developer; evidence can still be added
    SUBMITTED = "submitted"  # sealed and waiting for verification (F3)
    VERIFIED = "verified"  # set by F3
    ISSUED = "issued"  # set by F3 issuance; the batch is published through F4


class EvidenceKind(enum.StrEnum):
    LAND_TITLE = "land_title"
    SURVEY = "survey"
    PHOTO = "photo"
    GPS = "gps"
    SPREADSHEET = "spreadsheet"
    ADDITIONALITY_PROOF = "additionality_proof"
    OTHER = "other"


class Project(TimestampMixin, Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Public registry ID shown everywhere, e.g. CRVR-0147
    code: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    # Plain string (not an Enum column) so F3/F4 can add states without a migration here
    status: Mapped[str] = mapped_column(String(20), default="draft", server_default="draft")

    methodology: Mapped[str | None] = mapped_column(String(20))
    crediting_start_year: Mapped[int | None] = mapped_column(Integer)
    crediting_end_year: Mapped[int | None] = mapped_column(Integer)
    # As claimed by the developer; F2 computes the real area from the boundary
    area_ha: Mapped[float | None] = mapped_column(Float)
    est_removal_tco2e: Mapped[int | None] = mapped_column(Integer)
    baseline_summary: Mapped[str | None] = mapped_column(Text)
    additionality_reasoning: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class EvidenceFile(Base):
    """One uploaded evidence file. Write-once: a database trigger rejects UPDATE and DELETE."""

    __tablename__ = "evidence_files"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    kind: Mapped[EvidenceKind] = mapped_column(
        Enum(
            EvidenceKind,
            native_enum=False,
            length=30,
            values_callable=lambda e: [k.value for k in e],
        )
    )
    filename: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(120))
    size_bytes: Mapped[int] = mapped_column(BigInteger)
    sha256: Mapped[str] = mapped_column(String(64))
    # Path relative to settings.storage_dir; the file there is never rewritten
    storage_key: Mapped[str] = mapped_column(String(200), unique=True)
    uploaded_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    sealed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class EvidenceKey(Base):
    """The AES-256-GCM key for one evidence file (#45, ADR 0010).

    Deliberately an ordinary table: no write-once trigger, `ON DELETE CASCADE` from the
    evidence row. Deleting a row here is how personal data is erased from sealed evidence —
    the ciphertext stays where it is and the `evidence_files` row is never touched.
    """

    __tablename__ = "evidence_keys"

    evidence_id: Mapped[int] = mapped_column(
        ForeignKey("evidence_files.id", ondelete="CASCADE"), primary_key=True
    )
    key: Mapped[bytes] = mapped_column(LargeBinary(32))
    nonce: Mapped[bytes] = mapped_column(LargeBinary(12))


class EvidenceErasure(Base):
    """Why a file's key was destroyed, and what replaced it (#45).

    Append-only, like the evidence it describes: the row is the registry's record that the
    content is gone on purpose rather than lost. A file with an erasure row and no key row
    answers 410 instead of 404, so the audit trail still shows that evidence existed.
    """

    __tablename__ = "evidence_erasures"

    id: Mapped[int] = mapped_column(primary_key=True)
    evidence_id: Mapped[int] = mapped_column(
        ForeignKey("evidence_files.id"), unique=True, index=True
    )
    reason: Mapped[str] = mapped_column(String(500))
    # The redacted file uploaded in its place, when there is one. A verifier needs to be able
    # to follow the project's evidence after a page of it has been blacked out.
    replacement_id: Mapped[int | None] = mapped_column(ForeignKey("evidence_files.id"))
    erased_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    erased_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
