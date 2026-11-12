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
from app.features.boundary.rules import OverlapRule, exceeds_cap, exceeds_tolerance, rule_for
from app.features.registration.models import Project

# Why an overlap blocks (first rule broken, in this order) — `Overlap.reason`.
SHARE_OF_THIS = "share_of_this"  # above tolerance of the checked boundary's area
SHARE_OF_OTHER = "share_of_other"  # above tolerance of the other project's area
AREA_CAP = "area_cap"  # above the absolute area cap
COMBINED_SHARE = "combined_share"  # all overlaps together above tolerance of the checked area
COMBINED_AREA = "combined_area"  # all overlaps together above the area cap

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
    other_overlap_pct: float  # % of the other project's area
    rule: OverlapRule  # the stricter of the two projects' rules
    reason: str | None  # why it blocks (one of the constants above), None when within limits
    intersection: dict[str, Any]  # GeoJSON geometry of the shared area

    @property
    def exceeds_tolerance(self) -> bool:
        return self.reason is not None


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
    rule: OverlapRule,
    exclude_project_id: int | None = None,
) -> list[Overlap]:
    """Every registered boundary that shares area with `geometry`, largest overlap first.

    Boundaries that only touch along an edge share no area and are not returned.

    `rule` is the checked project's own rule. Each pair uses the stricter of the two projects'
    rules. An overlap blocks if it is more than the tolerance of **either** project's area (a
    large new boundary swallowing a small project) or more than the area cap (a large project
    double-counting many hectares under the percentage), or if all overlaps **together** break
    the checked project's tolerance or cap (many slivers that are each small).
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
            Project.methodology,
            Boundary.area_m2,
            shared_m2,
            func.ST_AsGeoJSON(shared),
        )
        .join(Project, Project.id == Boundary.project_id)
        .where(func.ST_Intersects(Boundary.geom, g))
    )
    if exclude_project_id is not None:
        stmt = stmt.where(Boundary.project_id != exclude_project_id)

    rows = [row for row in db.execute(stmt) if row[6] >= 1]  # skip touching edges / corners
    total_m2 = sum(m2 for *_, m2, _ in rows)
    total_pct = total_m2 / geometry.area_m2 * 100
    combined = (
        COMBINED_SHARE
        if exceeds_tolerance(total_pct, rule.tolerance_pct)
        else COMBINED_AREA
        if exceeds_cap(total_m2, rule.cap_ha)
        else None
    )

    overlaps = []
    for project_id, code, name, created_at, methodology, other_area_m2, m2, intersection in rows:
        pct = m2 / geometry.area_m2 * 100
        other_pct = m2 / other_area_m2 * 100
        pair = rule.stricter(rule_for(methodology))
        overlaps.append(
            Overlap(
                project_id=project_id,
                project_code=code,
                project_name=name,
                registered_at=created_at,
                overlap_m2=m2,
                overlap_pct=pct,
                other_overlap_pct=other_pct,
                rule=pair,
                reason=pair_reason(pct, other_pct, m2, pair) or combined,
                intersection=json.loads(intersection),
            )
        )
    return sorted(overlaps, key=lambda o: o.overlap_m2, reverse=True)


def pair_reason(pct: float, other_pct: float, m2: float, rule: OverlapRule) -> str | None:
    """Why an overlap between two projects blocks under `rule`, or None if it does not."""
    if exceeds_tolerance(pct, rule.tolerance_pct):
        return SHARE_OF_THIS
    if exceeds_tolerance(other_pct, rule.tolerance_pct):
        return SHARE_OF_OTHER
    if exceeds_cap(m2, rule.cap_ha):
        return AREA_CAP
    return None


def count_other_boundaries(db: Session, exclude_project_id: int | None = None) -> int:
    stmt = select(func.count()).select_from(Boundary)
    if exclude_project_id is not None:
        stmt = stmt.where(Boundary.project_id != exclude_project_id)
    return db.scalar(stmt) or 0
