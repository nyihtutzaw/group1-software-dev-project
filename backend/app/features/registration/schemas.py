from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.features.registration.models import EvidenceKind

# Methodologies offered in the form (mock-up + the mangrove demo project)
Methodology = Literal["VM0047", "VM0042", "ACM0003", "VM0033"]


class ProjectIn(BaseModel):
    """Create or update a draft. Everything except the name may be left for later."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    name: str = Field(min_length=3, max_length=200)
    methodology: Methodology | None = None
    crediting_start_year: int | None = Field(default=None, ge=2000, le=2100)
    crediting_end_year: int | None = Field(default=None, ge=2000, le=2200)
    area_ha: float | None = Field(default=None, gt=0, le=10_000_000)
    est_removal_tco2e: int | None = Field(default=None, gt=0, le=1_000_000_000)
    baseline_summary: str | None = Field(default=None, max_length=5000)
    additionality_reasoning: str | None = Field(default=None, max_length=10_000)


class EvidenceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    kind: EvidenceKind
    filename: str
    content_type: str
    size_bytes: int
    sha256: str
    sealed_at: datetime


class ProjectOut(BaseModel):
    """A row on the dashboard. F2's map picker uses id, code, name and status."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    status: str
    created_at: datetime
    methodology: str | None
    area_ha: float | None
    est_removal_tco2e: int | None
    submitted_at: datetime | None
    evidence_count: int = 0
    # An open or disputed F2 overlap flag — shown as OVERLAP, needs the developer's action
    overlap: bool = False


class ProjectDetail(ProjectOut):
    owner_name: str
    owner_organization: str | None
    crediting_start_year: int | None
    crediting_end_year: int | None
    baseline_summary: str | None
    additionality_reasoning: str | None
    updated_at: datetime
    evidence: list[EvidenceOut]
    # Human-readable list of what is still needed before the draft can be submitted
    missing: list[str]
    # F2: why the boundary blocks submission/issuance, or None when it is clear
    boundary_blocked: str | None
    can_edit: bool
