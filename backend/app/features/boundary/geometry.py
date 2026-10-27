"""Geometry checks for F2, done in PostGIS.

All spatial maths runs in the database (design report: "polygon intersection is a database
operation rather than something we implement ourselves"). Areas are computed on the geography
type, so they are true square metres on the WGS 84 ellipsoid.
"""

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from geoalchemy2 import Geography
from sqlalchemy import Float, cast, func, select
from sqlalchemy.orm import Session

from app.features.boundary.models import Boundary
from app.features.registration.models import Project

# A field-drawn or surveyed parcel never needs more; protects the overlap query.
MAX_VERTICES = 10_000


class BoundaryError(ValueError):
    """The submitted geometry cannot be used as a project boundary. Message is user-facing."""


@dataclass(frozen=True)
class CheckedGeometry:
    ewkt: str  # SRID=4326;MULTIPOLYGON(...) — normalised, ready to store
    area_m2: float
    vertices: int


@dataclass(frozen=True)
class Overlap:
    project_id: int
    project_code: str
    project_name: str
    registered_at: datetime
    overlap_m2: float
    overlap_pct: float  # % of the checked boundary's area
    exceeds_tolerance: bool
    intersection: dict[str, Any]  # GeoJSON geometry of the shared area


def exceeds_tolerance(overlap_pct: float, tolerance_pct: float) -> bool:
    """True if the overlap is above tolerance. Compared at the 2 decimals shown to users,
    so "0.50%" against a 0.5% tolerance is never blocked."""
    return round(overlap_pct, 2) > tolerance_pct


def _check_shape(geojson: Any) -> None:
    """Cheap structural checks before PostGIS sees the input, with readable messages."""
    if not isinstance(geojson, dict) or geojson.get("type") not in ("Polygon", "MultiPolygon"):
        raise BoundaryError("A boundary must be a Polygon or MultiPolygon.")
    coords = geojson.get("coordinates")
    if not isinstance(coords, list) or not coords:
        raise BoundaryError("The boundary has no coordinates.")
    polygons = [coords] if geojson["type"] == "Polygon" else coords
    for polygon in polygons:
        if not isinstance(polygon, list) or not polygon:
            raise BoundaryError("The boundary has an empty polygon.")
        for ring in polygon:
            if not isinstance(ring, list) or len(ring) < 4:
                raise BoundaryError("Each boundary ring needs at least 3 distinct corners.")
            for point in ring:
                if (
                    not isinstance(point, list | tuple)
                    or len(point) < 2
                    or not all(isinstance(v, int | float) for v in point[:2])
                ):
                    raise BoundaryError("Coordinates must be [longitude, latitude] numbers.")
                lon, lat = point[0], point[1]
                if not (-180 <= lon <= 180 and -90 <= lat <= 90):
                    raise BoundaryError(
                        "Coordinates must be WGS 84 longitude/latitude in degrees "
                        f"(got {lon}, {lat})."
                    )
            if ring[0][:2] != ring[-1][:2]:
                raise BoundaryError("Each boundary ring must end where it starts.")


def check_geometry(db: Session, geojson: Any) -> CheckedGeometry:
    """Validate a GeoJSON polygon and compute its true area. Raises BoundaryError."""
    _check_shape(geojson)

    g = func.ST_SetSRID(func.ST_Force2D(func.ST_GeomFromGeoJSON(json.dumps(geojson))), 4326)
    row = db.execute(
        select(
            func.ST_IsValid(g),
            func.ST_IsValidReason(g),
            func.ST_AsEWKT(func.ST_Multi(g)),
            func.ST_Area(cast(g, Geography), type_=Float),
            func.ST_NPoints(g) - func.ST_NRings(g),
        )
    ).one()
    is_valid, reason, ewkt, area_m2, vertices = row

    if not is_valid:
        # e.g. "Self-intersection[100.1 18.2]" — the edges of the shape cross each other
        raise BoundaryError(f"The boundary shape is not valid: {reason}.")
    if vertices > MAX_VERTICES:
        raise BoundaryError(f"The boundary has {vertices} corners; the limit is {MAX_VERTICES}.")
    if area_m2 < 1:
        raise BoundaryError("The boundary has no area.")
    return CheckedGeometry(ewkt=ewkt, area_m2=area_m2, vertices=vertices)


def find_overlaps(
    db: Session,
    geometry: CheckedGeometry,
    *,
    tolerance_pct: float,
    exclude_project_id: int | None = None,
) -> list[Overlap]:
    """Every registered boundary that shares area with `geometry`, largest overlap first.

    Boundaries that only touch along an edge share no area and are not returned.
    """
    g = func.ST_GeomFromEWKT(geometry.ewkt)
    shared = func.ST_Intersection(Boundary.geom, g)
    shared_m2 = func.ST_Area(cast(shared, Geography), type_=Float)

    stmt = (
        select(
            Project.id,
            Project.code,
            Project.name,
            Project.created_at,
            shared_m2,
            func.ST_AsGeoJSON(shared),
        )
        .join(Project, Project.id == Boundary.project_id)
        .where(func.ST_Intersects(Boundary.geom, g))
    )
    if exclude_project_id is not None:
        stmt = stmt.where(Boundary.project_id != exclude_project_id)

    overlaps = []
    for project_id, code, name, created_at, m2, intersection in db.execute(stmt):
        if m2 < 1:  # touching edges / corners only
            continue
        pct = m2 / geometry.area_m2 * 100
        overlaps.append(
            Overlap(
                project_id=project_id,
                project_code=code,
                project_name=name,
                registered_at=created_at,
                overlap_m2=m2,
                overlap_pct=pct,
                exceeds_tolerance=exceeds_tolerance(pct, tolerance_pct),
                intersection=json.loads(intersection),
            )
        )
    return sorted(overlaps, key=lambda o: o.overlap_m2, reverse=True)


def count_other_boundaries(db: Session, exclude_project_id: int | None = None) -> int:
    stmt = select(func.count()).select_from(Boundary)
    if exclude_project_id is not None:
        stmt = stmt.where(Boundary.project_id != exclude_project_id)
    return db.scalar(stmt) or 0
