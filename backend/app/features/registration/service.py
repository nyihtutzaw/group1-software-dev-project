"""F1 Project registration & evidence — business rules.

Evidence is write-once (FR-02, WBS 4.2.2): there is no code path that updates or deletes a stored
file or its row, the file is created with exclusive mode and made read-only, and a database
trigger rejects UPDATE/DELETE on `evidence_files`. Production swaps the volume for a Cloud
Storage bucket with a retention lock.
"""

import hashlib
from datetime import UTC, datetime
from pathlib import Path
from typing import BinaryIO
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import ColumnElement, Exists, ScalarSelect, exists, func, select, text
from sqlalchemy.orm import Session

from app.auth.models import Role, User
from app.core.config import get_settings
from app.features.audit.ledger import record_action
from app.features.boundary.models import BLOCKING_STATUSES, OverlapFlag
from app.features.boundary.service import issuance_blocked
from app.features.registration.models import EvidenceFile, EvidenceKind, Project, ProjectStatus
from app.features.registration.schemas import EvidenceOut, ProjectDetail, ProjectIn, ProjectOut

# FR-02 / WBS 4.2.1: documents, photographs, spreadsheets, GPS and land records
EVIDENCE_EXTENSIONS = {
    # documents and scanned land titles
    ".pdf",
    # photographs
    ".jpg",
    ".jpeg",
    ".png",
    ".heic",
    ".webp",
    ".tif",
    ".tiff",
    # spreadsheets
    ".xlsx",
    ".xls",
    ".ods",
    ".csv",
    # GPS / geospatial
    ".gpx",
    ".kml",
    ".kmz",
    ".geojson",
    # bundles, e.g. a set of geo-tagged photos or a zipped shapefile
    ".zip",
}
ACCEPTED_FORMATS = (
    "PDF, photos (JPG, PNG, HEIC, WebP, TIFF), spreadsheets (XLSX, XLS, ODS, CSV), "
    "GPS files (GPX, KML, KMZ, GeoJSON) and ZIP archives"
)

MAX_CREDITING_YEARS = 100
MIN_ADDITIONALITY_CHARS = 50
CHUNK = 1024 * 1024


# --- access ---------------------------------------------------------------------------


def get_project(db: Session, project_id: int, user: User, *, write: bool = False) -> Project:
    """Load a project the user may see, or with `write=True` one they may still change.

    Developers only reach their own projects and verifiers only submitted ones; anything else
    answers 404 so project IDs are not leaked.
    """
    project = db.get(Project, project_id)
    hidden = project is None or (
        (user.role == Role.DEVELOPER and project.owner_id != user.id)
        or (user.role == Role.VERIFIER and project.status == ProjectStatus.DRAFT)
        or user.role == Role.BUYER
    )
    if hidden:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
    if write:
        if user.role != Role.DEVELOPER:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN, "Only the project's developer can change it"
            )
        if project.status != ProjectStatus.DRAFT:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "This project has been submitted and is sealed — it can no longer be changed",
            )
    return project


def can_edit(project: Project, user: User) -> bool:
    return (
        user.role == Role.DEVELOPER
        and project.owner_id == user.id
        and project.status == ProjectStatus.DRAFT
    )


# --- drafts ---------------------------------------------------------------------------


def _next_code(db: Session) -> str:
    return f"CRVR-{db.scalar(text("SELECT nextval('project_code_seq')")):04d}"


def _check_period(data: ProjectIn) -> None:
    start, end = data.crediting_start_year, data.crediting_end_year
    if start is None or end is None:
        return
    if end <= start:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "The crediting period must end after it starts"
        )
    if end - start > MAX_CREDITING_YEARS:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            f"The crediting period cannot be longer than {MAX_CREDITING_YEARS} years",
        )


def create_project(db: Session, owner: User, data: ProjectIn) -> Project:
    _check_period(data)
    project = Project(code=_next_code(db), owner_id=owner.id, **data.model_dump())
    db.add(project)
    db.flush()
    record_action(db, actor=owner, action="project.created", entity="project", entity_id=project.id)
    db.commit()
    db.refresh(project)
    return project


def update_project(db: Session, project: Project, data: ProjectIn) -> Project:
    """Replace a draft's fields with what the form sends (save draft / continue)."""
    _check_period(data)
    for field, value in data.model_dump().items():
        setattr(project, field, value)
    db.commit()
    db.refresh(project)
    return project


# --- evidence -------------------------------------------------------------------------


def _evidence(db: Session, project_id: int) -> list[EvidenceFile]:
    stmt = select(EvidenceFile).where(EvidenceFile.project_id == project_id)
    return list(db.scalars(stmt.order_by(EvidenceFile.id)).all())


def store_evidence(
    db: Session,
    project: Project,
    user: User,
    *,
    kind: EvidenceKind,
    filename: str,
    content_type: str | None,
    stream: BinaryIO,
) -> EvidenceFile:
    """Write an uploaded file once and seal it. The bytes are hashed as they are written."""
    name = Path(filename.replace("\\", "/")).name.strip()
    if not name:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "The file has no name")
    ext = Path(name).suffix.lower()
    if ext not in EVIDENCE_EXTENSIONS:
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            f"“{name}” is not an accepted evidence format. Accepted: {ACCEPTED_FORMATS}.",
        )

    settings = get_settings()
    key = f"{project.id}/{uuid4().hex}{ext}"
    path = Path(settings.storage_dir) / key
    path.parent.mkdir(parents=True, exist_ok=True)

    digest, size, too_large = hashlib.sha256(), 0, False
    # "xb": fail rather than overwrite if the key somehow exists
    with path.open("xb") as out:
        while chunk := stream.read(CHUNK):
            size += len(chunk)
            if size > settings.evidence_max_bytes:
                too_large = True
                break
            digest.update(chunk)
            out.write(chunk)
    if too_large or size == 0:
        # Not sealed yet — nothing references this partial file
        path.unlink()
        if too_large:
            raise HTTPException(
                status.HTTP_413_CONTENT_TOO_LARGE,
                f"“{name}” is larger than {settings.evidence_max_bytes / (1024 * 1024):g} MB",
            )
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, f"“{name}” is empty")
    path.chmod(0o444)

    evidence = EvidenceFile(
        project_id=project.id,
        kind=kind,
        filename=name[:255],
        content_type=(content_type or "application/octet-stream")[:120],
        size_bytes=size,
        sha256=digest.hexdigest(),
        storage_key=key,
        uploaded_by_id=user.id,
    )
    db.add(evidence)
    db.flush()
    record_action(
        db,
        actor=user,
        action="evidence.sealed",
        entity="project",
        entity_id=project.id,
        payload={
            "evidence_id": evidence.id,
            "kind": kind.value,
            "filename": evidence.filename,
            "sha256": evidence.sha256,
            "size_bytes": size,
        },
    )
    db.commit()
    db.refresh(evidence)
    return evidence


def get_evidence(db: Session, project: Project, evidence_id: int) -> tuple[EvidenceFile, Path]:
    evidence = db.get(EvidenceFile, evidence_id)
    if evidence is None or evidence.project_id != project.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Evidence file not found")
    path = Path(get_settings().storage_dir) / evidence.storage_key
    if not path.is_file():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "The stored file is missing")
    return evidence, path


# --- submission -----------------------------------------------------------------------


def missing_for_submission(db: Session, project: Project) -> list[str]:
    """Everything still needed before submission, in form order. Empty means complete."""
    missing = []
    if not project.methodology:
        missing.append("Methodology")
    if project.crediting_start_year is None or project.crediting_end_year is None:
        missing.append("Crediting period")
    if project.area_ha is None:
        missing.append("Area (ha)")
    if project.est_removal_tco2e is None:
        missing.append("Estimated removal (tCO₂e)")
    if not (project.baseline_summary or "").strip():
        missing.append("Baseline summary")
    if len((project.additionality_reasoning or "").strip()) < MIN_ADDITIONALITY_CHARS:
        missing.append(f"Additionality reasoning (at least {MIN_ADDITIONALITY_CHARS} characters)")

    kinds = [e.kind for e in _evidence(db, project.id)]
    if EvidenceKind.ADDITIONALITY_PROOF not in kinds:
        missing.append("Additionality proof upload")
    if not any(k != EvidenceKind.ADDITIONALITY_PROOF for k in kinds):
        missing.append("At least one evidence file (land title, survey, photos or GPS)")

    blocked = issuance_blocked(db, project.id)
    if blocked:
        missing.append(blocked)
    return missing


def submit_project(db: Session, project: Project, user: User) -> Project:
    missing = missing_for_submission(db, project)
    if missing:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "This project cannot be submitted yet. Still needed: " + "; ".join(missing) + ".",
        )
    project.status = ProjectStatus.SUBMITTED
    project.submitted_at = datetime.now(UTC)
    record_action(
        db,
        actor=user,
        action="project.submitted",
        entity="project",
        entity_id=project.id,
        payload={
            "code": project.code,
            "evidence_sha256": [e.sha256 for e in _evidence(db, project.id)],
        },
    )
    db.commit()
    db.refresh(project)
    return project


# --- read models ----------------------------------------------------------------------


def _evidence_count() -> ScalarSelect[int]:
    return (
        select(func.count(EvidenceFile.id))
        .where(EvidenceFile.project_id == Project.id)
        .correlate(Project)
        .scalar_subquery()
    )


def _has_overlap(project_id: ColumnElement[int] | int) -> Exists:
    """An open or disputed F2 overlap flag on the project."""
    return exists().where(
        OverlapFlag.project_id == project_id, OverlapFlag.status.in_(BLOCKING_STATUSES)
    )


def list_projects(db: Session, user: User) -> list[ProjectOut]:
    """Developers see their own projects; everyone else allowed here sees all."""
    stmt = select(Project, _evidence_count(), _has_overlap(Project.id)).order_by(Project.code)
    if user.role == Role.DEVELOPER:
        stmt = stmt.where(Project.owner_id == user.id)
    return [
        ProjectOut.model_validate(project).model_copy(
            update={"evidence_count": count, "overlap": overlap}
        )
        for project, count, overlap in db.execute(stmt)
    ]


def project_detail(db: Session, project: Project, user: User) -> ProjectDetail:
    owner = db.get(User, project.owner_id)
    evidence = _evidence(db, project.id)
    # Columns copied straight from the project; the rest is computed below
    columns = {f: getattr(project, f) for f in ProjectDetail.model_fields if hasattr(project, f)}
    return ProjectDetail(
        **columns,
        evidence_count=len(evidence),
        overlap=bool(db.scalar(select(_has_overlap(project.id)))),
        owner_name=owner.full_name if owner else "",
        owner_organization=owner.organization if owner else None,
        evidence=[EvidenceOut.model_validate(e) for e in evidence],
        missing=(
            missing_for_submission(db, project) if project.status == ProjectStatus.DRAFT else []
        ),
        boundary_blocked=issuance_blocked(db, project.id),
        can_edit=can_edit(project, user),
    )
