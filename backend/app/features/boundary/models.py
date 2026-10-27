"""F2 Geospatial boundary & overlap detection — database tables."""

import enum
from datetime import datetime

from geoalchemy2 import Geometry, WKBElement
from sqlalchemy import DateTime, Enum, Float, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, TimestampMixin


class BoundarySource(enum.StrEnum):
    DRAWN = "drawn"
    UPLOADED = "uploaded"


class FlagStatus(enum.StrEnum):
    OPEN = "open"  # overlap above tolerance, not yet looked at
    DISPUTED = "disputed"  # developer says the other boundary is wrong; staff must decide
    RESOLVED = "resolved"  # registry staff investigated and cleared it
    SUPERSEDED = "superseded"  # the boundary was redrawn; a fresh check replaced this flag


# Flags in these states block credit issuance (FR-04, WBS 5.3.2).
BLOCKING_STATUSES = (FlagStatus.OPEN, FlagStatus.DISPUTED)


def _enum(cls: type[enum.StrEnum]) -> Enum:
    return Enum(cls, native_enum=False, length=20, values_callable=lambda e: [m.value for m in e])


class Boundary(TimestampMixin, Base):
    """The current boundary of a project — one per project, replaced when redrawn."""

    __tablename__ = "boundaries"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), unique=True)
    # WGS 84 lon/lat; GeoAlchemy2 adds a GiST spatial index automatically
    geom: Mapped[WKBElement] = mapped_column(Geometry("MULTIPOLYGON", srid=4326))
    # Computed by PostGIS on the geography (square metres) — never taken from the user
    area_m2: Mapped[float] = mapped_column(Float)
    source: Mapped[BoundarySource] = mapped_column(_enum(BoundarySource))
    updated_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class OverlapFlag(TimestampMixin, Base):
    """An overlap above tolerance between a project's boundary and an earlier one."""

    __tablename__ = "overlap_flags"

    id: Mapped[int] = mapped_column(primary_key=True)
    # The project whose boundary caused the overlap (the later registration)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    # The already-registered project it overlaps
    other_project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    overlap_m2: Mapped[float] = mapped_column(Float)
    overlap_pct: Mapped[float] = mapped_column(Float)
    status: Mapped[FlagStatus] = mapped_column(
        _enum(FlagStatus), default=FlagStatus.OPEN, server_default=FlagStatus.OPEN.value
    )
    dispute_reason: Mapped[str | None] = mapped_column(Text)
    resolution_note: Mapped[str | None] = mapped_column(Text)
    resolved_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
