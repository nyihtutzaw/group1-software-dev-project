"""F2 Geospatial boundary & overlap detection — API routes, mounted under /api/boundaries."""

import json
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.deps import require_roles
from app.auth.models import Role, User
from app.core.config import get_settings
from app.core.db import get_db
from app.features.boundary import service
from app.features.boundary.geometry import BoundaryError
from app.features.boundary.importers import parse_boundary_file
from app.features.boundary.models import BLOCKING_STATUSES, Boundary, OverlapFlag
from app.features.boundary.schemas import (
    M2_PER_HA,
    BoundaryOut,
    CheckIn,
    CheckOut,
    DisputeIn,
    FlagOut,
    ImportOut,
    ResolveIn,
    SaveIn,
)
from app.features.registration.models import Project

router = APIRouter(prefix="/boundaries", tags=["F2 boundary"])

MAP_ROLES = (Role.DEVELOPER, Role.VERIFIER, Role.REGISTRY_STAFF, Role.ADMIN)
EDIT_ROLES = (Role.DEVELOPER, Role.ADMIN)


def _invalid(exc: BoundaryError) -> HTTPException:
    return HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc))


@router.get("")
def list_boundaries(
    db: Session = Depends(get_db), user: User = Depends(require_roles(*MAP_ROLES))
) -> dict[str, Any]:
    """Every registered boundary as a GeoJSON FeatureCollection, for the map's context layer."""
    blocked = (
        select(OverlapFlag.project_id)
        .where(OverlapFlag.status.in_(BLOCKING_STATUSES))
        .distinct()
        .scalar_subquery()
    )
    rows = db.execute(
        select(
            Project.id,
            Project.code,
            Project.name,
            Boundary.area_m2,
            Project.id.in_(blocked),
            func.ST_AsGeoJSON(Boundary.geom),
        )
        .join(Project, Project.id == Boundary.project_id)
        .order_by(Project.code)
    )
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": json.loads(geometry),
                "properties": {
                    "project_id": project_id,
                    "code": code,
                    "name": name,
                    "area_ha": area_m2 / M2_PER_HA,
                    "flagged": flagged,
                },
            }
            for project_id, code, name, area_m2, flagged, geometry in rows
        ],
    }


@router.post("/check", response_model=CheckOut)
def check(
    body: CheckIn, db: Session = Depends(get_db), user: User = Depends(require_roles(*MAP_ROLES))
) -> CheckOut:
    """Validate a boundary and screen it for overlaps without saving anything."""
    try:
        return CheckOut.build(service.check_boundary(db, body.geometry, body.project_id))
    except BoundaryError as exc:
        raise _invalid(exc) from exc


@router.post("/import", response_model=ImportOut)
async def import_file(
    file: UploadFile = File(...), user: User = Depends(require_roles(*EDIT_ROLES))
) -> ImportOut:
    """Read a boundary from GeoJSON, KML/KMZ or a zipped shapefile. Nothing is saved."""
    limit = get_settings().boundary_upload_max_bytes
    data = await file.read(limit + 1)
    if len(data) > limit:
        raise HTTPException(
            status.HTTP_413_CONTENT_TOO_LARGE,
            f"The file is larger than {limit / (1024 * 1024):g} MB",
        )
    try:
        geometry = parse_boundary_file(file.filename or "", data)
    except BoundaryError as exc:
        raise _invalid(exc) from exc
    return ImportOut(filename=file.filename or "", geometry=geometry)


def _flag_out(db: Session, flag: OverlapFlag) -> FlagOut:
    other = db.get(Project, flag.other_project_id)
    return FlagOut(
        id=flag.id,
        other_project_id=flag.other_project_id,
        other_project_code=other.code if other else "",
        other_project_name=other.name if other else "",
        overlap_ha=flag.overlap_m2 / M2_PER_HA,
        overlap_pct=flag.overlap_pct,
        status=flag.status,
        dispute_reason=flag.dispute_reason,
        resolution_note=flag.resolution_note,
        created_at=flag.created_at,
        resolved_at=flag.resolved_at,
    )


def _boundary_out(
    db: Session, project: Project, user: User, result: service.BoundaryCheck | None = None
) -> BoundaryOut:
    boundary = service.get_boundary(db, project.id)
    if boundary is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No boundary has been registered yet")
    geometry = service.boundary_geojson(db, boundary)
    if result is None:
        result = service.check_boundary(db, geometry, project.id)
    flags = [_flag_out(db, f) for f in service.active_flags(db, project.id)]
    can_edit = user.role == Role.ADMIN or (
        user.role == Role.DEVELOPER and project.owner_id == user.id
    )
    return BoundaryOut(
        project_id=project.id,
        project_code=project.code,
        project_name=project.name,
        geometry=geometry,
        source=boundary.source,
        updated_at=boundary.updated_at,
        check=CheckOut.build(result),
        flags=flags,
        issuance_blocked=service.issuance_blocked(db, project.id),
        can_edit=can_edit,
    )


@router.get("/{project_id}", response_model=BoundaryOut)
def get_boundary(
    project_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*MAP_ROLES)),
) -> BoundaryOut:
    project = service.get_project(db, project_id, user)
    return _boundary_out(db, project, user)


@router.put("/{project_id}", response_model=BoundaryOut)
def save_boundary(
    project_id: int,
    body: SaveIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*EDIT_ROLES)),
) -> BoundaryOut:
    """Register or replace the project's boundary. Overlaps above tolerance are flagged."""
    project = service.get_project(db, project_id, user, write=True)
    try:
        result = service.save_boundary(db, project, body.geometry, body.source, user)
    except BoundaryError as exc:
        raise _invalid(exc) from exc
    # The save already screened this shape; reuse it rather than running the check again.
    return _boundary_out(db, project, user, result)


@router.post("/flags/{flag_id}/dispute", response_model=FlagOut)
def dispute(
    flag_id: int,
    body: DisputeIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*EDIT_ROLES)),
) -> FlagOut:
    """The project's developer disputes an overlap; registry staff then investigate."""
    return _flag_out(db, service.dispute_flag(db, flag_id, user, body.reason))


@router.post("/flags/{flag_id}/resolve", response_model=FlagOut)
def resolve(
    flag_id: int,
    body: ResolveIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(Role.REGISTRY_STAFF, Role.ADMIN)),
) -> FlagOut:
    """Registry staff clear an investigated overlap, which unblocks issuance."""
    return _flag_out(db, service.resolve_flag(db, flag_id, user, body.note))
