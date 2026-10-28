from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.features.boundary.geometry import Overlap
from app.features.boundary.models import BoundarySource, FlagStatus
from app.features.boundary.service import BoundaryCheck

GeoJSON = dict[str, Any]
M2_PER_HA = 10_000


class CheckIn(BaseModel):
    geometry: GeoJSON
    # When re-checking an existing project's boundary, leave its own boundary out
    project_id: int | None = None


class SaveIn(BaseModel):
    geometry: GeoJSON
    source: BoundarySource = BoundarySource.DRAWN


class DisputeIn(BaseModel):
    reason: str = Field(min_length=10, max_length=2000)


class ResolveIn(BaseModel):
    note: str = Field(min_length=5, max_length=2000)


class OverlapOut(BaseModel):
    project_id: int
    project_code: str
    project_name: str
    registered_at: datetime
    overlap_m2: float
    overlap_ha: float
    overlap_pct: float  # % of the checked boundary's area
    other_overlap_pct: float  # % of the other project's area
    exceeds_tolerance: bool
    intersection: GeoJSON

    @classmethod
    def build(cls, o: Overlap) -> "OverlapOut":
        return cls(
            project_id=o.project_id,
            project_code=o.project_code,
            project_name=o.project_name,
            registered_at=o.registered_at,
            overlap_m2=o.overlap_m2,
            overlap_ha=o.overlap_m2 / M2_PER_HA,
            overlap_pct=o.overlap_pct,
            other_overlap_pct=o.other_overlap_pct,
            exceeds_tolerance=o.exceeds_tolerance,
            intersection=o.intersection,
        )


class CheckOut(BaseModel):
    area_m2: float
    area_ha: float
    vertices: int
    checked_against: int
    tolerance_pct: float
    overlaps: list[OverlapOut]
    blocked: bool

    @classmethod
    def build(cls, c: BoundaryCheck) -> "CheckOut":
        return cls(
            area_m2=c.geometry.area_m2,
            area_ha=c.geometry.area_m2 / M2_PER_HA,
            vertices=c.geometry.vertices,
            checked_against=c.checked_against,
            tolerance_pct=c.tolerance_pct,
            overlaps=[OverlapOut.build(o) for o in c.overlaps],
            blocked=c.blocked,
        )


class FlagOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    other_project_id: int
    other_project_code: str
    other_project_name: str
    overlap_ha: float
    overlap_pct: float
    status: FlagStatus
    dispute_reason: str | None
    resolution_note: str | None
    created_at: datetime
    resolved_at: datetime | None


class BoundaryOut(BaseModel):
    project_id: int
    project_code: str
    project_name: str
    geometry: GeoJSON
    source: BoundarySource
    updated_at: datetime
    check: CheckOut
    flags: list[FlagOut]
    # Why issuance is blocked, or null when clear (FR-04)
    issuance_blocked: str | None
    can_edit: bool


class ImportOut(BaseModel):
    filename: str
    geometry: GeoJSON
