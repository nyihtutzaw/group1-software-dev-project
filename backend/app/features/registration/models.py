"""F1 Project registration & evidence — database tables.

`projects` started as a minimal stub added by F2; `id`, `code`, `name`, `owner_id` and
`created_at` are relied on by F2/F3/F4 — keep them. Registration fields are nullable because a
draft may be saved half-filled; `service.missing_for_submission()` decides what is complete.
"""

import enum
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Enum, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, TimestampMixin


class ProjectStatus(enum.StrEnum):
    DRAFT = "draft"  # being filled in by the developer; evidence can still be added
    SUBMITTED = "submitted"  # sealed and waiting for verification (F3)
    VERIFIED = "verified"  # set by F3
    ISSUED = "issued"  # set by F4


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
