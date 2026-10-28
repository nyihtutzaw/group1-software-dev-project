"""F2 business logic: checking, saving and flagging project boundaries."""

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException, status
from geoalchemy2 import Geography
from sqlalchemy import Float, cast, func, select
from sqlalchemy.orm import Session

from app.auth.models import Role, User
from app.core.config import get_settings
from app.features.audit.ledger import record_action
from app.features.boundary.geometry import (
    CheckedGeometry,
    Overlap,
    check_geometry,
    count_other_boundaries,
    exceeds_tolerance,
    find_overlaps,
)
from app.features.boundary.models import (
    BLOCKING_STATUSES,
    Boundary,
    BoundarySource,
    FlagStatus,
    OverlapFlag,
)
from app.features.registration.models import Project


@dataclass(frozen=True)
class BoundaryCheck:
    geometry: CheckedGeometry
    checked_against: int
    tolerance_pct: float
    overlaps: list[Overlap]

    @property
    def blocked(self) -> bool:
        return any(o.exceeds_tolerance for o in self.overlaps)


def check_boundary(db: Session, geojson: Any, project_id: int | None = None) -> BoundaryCheck:
    """Validate a boundary and screen it against every other registered boundary."""
    tolerance = get_settings().overlap_tolerance_pct
    checked = check_geometry(db, geojson)
    return BoundaryCheck(
        geometry=checked,
        checked_against=count_other_boundaries(db, exclude_project_id=project_id),
        tolerance_pct=tolerance,
        overlaps=find_overlaps(db, checked, tolerance_pct=tolerance, exclude_project_id=project_id),
    )


# --- access ---------------------------------------------------------------------------


def get_project(db: Session, project_id: int, user: User, *, write: bool = False) -> Project:
    """Load a project the user may see (or change). Developers only reach their own."""
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
    if user.role == Role.DEVELOPER and project.owner_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This is not your project")
    if write and user.role not in (Role.DEVELOPER, Role.ADMIN):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Your role cannot change boundaries")
    return project


def get_boundary(db: Session, project_id: int) -> Boundary | None:
    return db.scalar(select(Boundary).where(Boundary.project_id == project_id))


def boundary_geojson(db: Session, boundary: Boundary) -> dict[str, Any]:
    stmt = select(func.ST_AsGeoJSON(Boundary.geom)).where(Boundary.id == boundary.id)
    return json.loads(db.scalar(stmt))


def active_flags(db: Session, project_id: int) -> list[OverlapFlag]:
    """Flags still relevant to the current boundary (everything except superseded)."""
    return list(
        db.scalars(
            select(OverlapFlag)
            .where(
                OverlapFlag.project_id == project_id,
                OverlapFlag.status != FlagStatus.SUPERSEDED,
            )
            .order_by(OverlapFlag.overlap_m2.desc())
        )
    )


# --- save -----------------------------------------------------------------------------

# Each save screens against every other boundary, so two saves running at the same time could
# each miss the other (and two first saves of one project would collide on its unique row).
# A transaction-level advisory lock makes boundary saves take turns; it is released on commit.
BOUNDARY_SAVE_LOCK = 0x0F2B


def save_boundary(
    db: Session, project: Project, geojson: Any, source: BoundarySource, user: User
) -> BoundaryCheck:
    """Store the project's boundary, replace its overlap flags and record it in the ledger."""
    db.execute(select(func.pg_advisory_xact_lock(BOUNDARY_SAVE_LOCK)))
    result = check_boundary(db, geojson, project_id=project.id)
    checked = result.geometry

    boundary = get_boundary(db, project.id)
    if boundary is None:
        boundary = Boundary(project_id=project.id)
        db.add(boundary)
    boundary.geom = checked.ewkt
    boundary.area_m2 = checked.area_m2
    boundary.source = source
    boundary.updated_by_id = user.id

    # A redrawn boundary gets a fresh screening; every earlier flag (open, disputed or resolved)
    # described the old shape and no longer applies. Resolved ones keep their note and date.
    now = datetime.now(UTC)
    for flag in db.scalars(
        select(OverlapFlag).where(
            OverlapFlag.project_id == project.id, OverlapFlag.status != FlagStatus.SUPERSEDED
        )
    ):
        flag.status = FlagStatus.SUPERSEDED
        flag.resolved_at = flag.resolved_at or now

    _recheck_flags_against(db, project, checked, result.tolerance_pct, now)

    record_action(
        db,
        actor=user,
        action="boundary.saved",
        entity="project",
        entity_id=project.id,
        payload={
            "area_m2": round(checked.area_m2, 1),
            "vertices": checked.vertices,
            "source": source.value,
        },
    )
    for overlap in result.overlaps:
        if not overlap.exceeds_tolerance:
            continue
        db.add(
            OverlapFlag(
                project_id=project.id,
                other_project_id=overlap.project_id,
                overlap_m2=overlap.overlap_m2,
                overlap_pct=overlap.overlap_pct,
            )
        )
        record_action(
            db,
            actor=None,  # detected automatically by the geospatial check
            action="boundary.overlap_detected",
            entity="project",
            entity_id=project.id,
            payload={
                "other_project": overlap.project_code,
                "overlap_m2": round(overlap.overlap_m2, 1),
                "overlap_pct": round(overlap.overlap_pct, 2),
            },
        )

    db.commit()
    return result


def _recheck_flags_against(
    db: Session,
    project: Project,
    checked: CheckedGeometry,
    tolerance_pct: float,
    now: datetime,
) -> None:
    """Re-measure blocking flags other projects hold against `project`, whose shape just changed.

    Still above tolerance: keep the flag (and any dispute) with updated figures. Now within
    tolerance: supersede it, so the other project is no longer blocked by a shape that is gone.
    Pairwise only — the other project's combined-overlap rule is re-applied when it next saves.
    """
    new_shape = func.ST_GeomFromEWKT(checked.ewkt)
    flags = db.scalars(
        select(OverlapFlag).where(
            OverlapFlag.other_project_id == project.id,
            OverlapFlag.status.in_(BLOCKING_STATUSES),
        )
    )
    for flag in flags:
        holder = get_boundary(db, flag.project_id)
        if holder is None:
            continue
        shared_m2 = (
            db.scalar(
                select(
                    func.ST_Area(
                        cast(func.ST_Intersection(Boundary.geom, new_shape), Geography),
                        type_=Float,
                    )
                ).where(Boundary.id == holder.id)
            )
            or 0.0
        )
        holder_pct = shared_m2 / holder.area_m2 * 100
        changed_pct = shared_m2 / checked.area_m2 * 100
        if exceeds_tolerance(holder_pct, tolerance_pct) or exceeds_tolerance(
            changed_pct, tolerance_pct
        ):
            flag.overlap_m2 = shared_m2
            flag.overlap_pct = holder_pct
            continue
        flag.status = FlagStatus.SUPERSEDED
        flag.resolved_at = now
        flag.resolution_note = (
            f"{project.code} changed its boundary; the overlap is now within tolerance."
        )
        record_action(
            db,
            actor=None,
            action="boundary.overlap_cleared",
            entity="project",
            entity_id=flag.project_id,
            payload={"other_project": project.code, "overlap_m2": round(shared_m2, 1)},
        )


# --- flags ----------------------------------------------------------------------------


def _get_flag(db: Session, flag_id: int) -> OverlapFlag:
    flag = db.get(OverlapFlag, flag_id)
    if flag is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Overlap flag not found")
    return flag


def dispute_flag(db: Session, flag_id: int, user: User, reason: str) -> OverlapFlag:
    """The developer says the other boundary is wrong. Staff must then investigate."""
    flag = _get_flag(db, flag_id)
    get_project(db, flag.project_id, user, write=True)
    if flag.status != FlagStatus.OPEN:
        raise HTTPException(status.HTTP_409_CONFLICT, f"This overlap is already {flag.status}")
    flag.status = FlagStatus.DISPUTED
    flag.dispute_reason = reason
    record_action(
        db,
        actor=user,
        action="boundary.overlap_disputed",
        entity="project",
        entity_id=flag.project_id,
        payload={"flag_id": flag.id, "reason": reason},
    )
    db.commit()
    return flag


def resolve_flag(db: Session, flag_id: int, user: User, note: str) -> OverlapFlag:
    """Registry staff clear an overlap after investigating it (unblocks issuance)."""
    flag = _get_flag(db, flag_id)
    project = db.get(Project, flag.project_id)
    if project is not None and project.owner_id == user.id:
        # Separation of duties (FR-10): nobody clears a flag on their own project.
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You cannot resolve your own project")
    if flag.status not in BLOCKING_STATUSES:
        raise HTTPException(status.HTTP_409_CONFLICT, f"This overlap is already {flag.status}")
    flag.status = FlagStatus.RESOLVED
    flag.resolution_note = note
    flag.resolved_by_id = user.id
    flag.resolved_at = datetime.now(UTC)
    record_action(
        db,
        actor=user,
        action="boundary.overlap_resolved",
        entity="project",
        entity_id=flag.project_id,
        payload={"flag_id": flag.id, "note": note},
    )
    db.commit()
    return flag


# --- issuance gate (for F3 / F4) ------------------------------------------------------


def issuance_blocked(db: Session, project_id: int) -> str | None:
    """Why credits cannot be issued for this project yet, or None if the boundary is clear.

    F3/F4: call this before approving or issuing — FR-04, WBS 5.3.2.
    """
    if get_boundary(db, project_id) is None:
        return "No boundary has been registered for this project."
    blocking = db.scalar(
        select(func.count())
        .select_from(OverlapFlag)
        .where(OverlapFlag.project_id == project_id, OverlapFlag.status.in_(BLOCKING_STATUSES))
    )
    if blocking:
        return "The boundary overlaps another project and has not been resolved."
    return None
