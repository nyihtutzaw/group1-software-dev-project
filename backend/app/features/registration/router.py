"""F1 Project registration & evidence — API routes, mounted under /api/projects.

There is deliberately no PUT/PATCH/DELETE for evidence: uploaded files are write-once.
"""

from collections.abc import Iterator
from contextlib import closing
from typing import BinaryIO
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.auth.deps import require_roles
from app.auth.models import Role, User
from app.core.db import get_db
from app.features.registration import service
from app.features.registration.media import viewable_type
from app.features.registration.models import EvidenceErasure, EvidenceFile, EvidenceKind
from app.features.registration.schemas import (
    EvidenceErasureIn,
    EvidenceErasureOut,
    EvidenceOut,
    ProjectDetail,
    ProjectIn,
    ProjectOut,
)
from app.features.registration.storage import CHUNK

router = APIRouter(prefix="/projects", tags=["F1 registration"])

LIST_ROLES = (Role.DEVELOPER, Role.REGISTRY_STAFF, Role.ADMIN)
# Verifiers may open submitted projects assigned to them (see service.get_project)
READ_ROLES = (Role.DEVELOPER, Role.VERIFIER, Role.REGISTRY_STAFF, Role.ADMIN)


@router.get("", response_model=list[ProjectOut])
def list_projects(
    db: Session = Depends(get_db), user: User = Depends(require_roles(*LIST_ROLES))
) -> list[ProjectOut]:
    """Developers see their own projects; registry staff and admins see all."""
    return service.list_projects(db, user)


@router.post("", response_model=ProjectDetail, status_code=201)
def create_project(
    body: ProjectIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(Role.DEVELOPER)),
) -> ProjectDetail:
    """Start a draft. Only the name is needed now; the rest can be saved later."""
    project = service.create_project(db, owner=user, data=body)
    return service.project_detail(db, project, user)


@router.get("/{project_id}", response_model=ProjectDetail)
def get_project(
    project_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*READ_ROLES)),
) -> ProjectDetail:
    project = service.get_project(db, project_id, user)
    return service.project_detail(db, project, user)


@router.put("/{project_id}", response_model=ProjectDetail)
def update_project(
    project_id: int,
    body: ProjectIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(Role.DEVELOPER)),
) -> ProjectDetail:
    """Save the draft's fields (Save draft / Continue). Rejected once submitted."""
    project = service.get_project(db, project_id, user, write=True)
    service.update_project(db, project, body)
    return service.project_detail(db, project, user)


@router.post("/{project_id}/submit", response_model=ProjectDetail)
def submit_project(
    project_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(Role.DEVELOPER)),
) -> ProjectDetail:
    """Submit a complete draft for verification; 422 lists what is still missing."""
    project = service.get_project(db, project_id, user, write=True)
    service.submit_project(db, project, user)
    return service.project_detail(db, project, user)


@router.post("/{project_id}/evidence", response_model=EvidenceOut, status_code=201)
def upload_evidence(
    project_id: int,
    file: UploadFile = File(...),
    kind: EvidenceKind = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(Role.DEVELOPER)),
) -> EvidenceFile:
    """Upload one evidence file to a draft. It is sealed at once and can never be replaced."""
    project = service.get_project(db, project_id, user, write=True)
    return service.store_evidence(
        db,
        project,
        user,
        kind=kind,
        filename=file.filename or "",
        content_type=file.content_type,
        stream=file.file,
    )


@router.post(
    "/{project_id}/evidence/{evidence_id}/erasure",
    response_model=EvidenceErasureOut,
    status_code=201,
)
def erase_evidence(
    project_id: int,
    evidence_id: int,
    body: EvidenceErasureIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(Role.ADMIN)),
) -> EvidenceErasure:
    """Destroy one evidence file's encryption key so its content can no longer be read (#45).

    This is the only way personal data leaves sealed evidence. Nothing is deleted except the
    key: the sealed object and its row stay, and the ledger keeps the original SHA-256. Admin
    only, and it cannot be undone.
    """
    project = service.get_project(db, project_id, user)
    return service.erase_evidence(
        db,
        project,
        user,
        evidence_id=evidence_id,
        reason=body.reason,
        replacement_id=body.replacement_id,
    )


@router.get("/{project_id}/evidence/{evidence_id}/file")
def download_evidence(
    project_id: int,
    evidence_id: int,
    inline: bool = Query(False, description="Show a PDF or photo in the browser (View)"),
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*READ_ROLES)),
) -> StreamingResponse:
    """Stream the sealed bytes, from the local volume or the bucket — the route is the same.

    `inline=true` lets the browser show the file (a verifier reads it before signing off), but
    only for PDFs and photos, served with the type of their extension and `nosniff`; any other
    file is still sent as a download.
    """
    project = service.get_project(db, project_id, user)
    evidence, stream = service.get_evidence(db, project, evidence_id)
    shown_as = viewable_type(evidence.filename) if inline else None
    return StreamingResponse(
        _chunks(stream),
        media_type=shown_as or evidence.content_type,
        headers={
            "content-disposition": _disposition(
                "inline" if shown_as else "attachment", evidence.filename
            ),
            "content-length": str(evidence.size_bytes),
            "x-content-type-options": "nosniff",
        },
    )


def _disposition(kind: str, filename: str) -> str:
    """Content-Disposition that keeps non-ASCII names (e.g. Thai) intact (RFC 6266)."""
    fallback = filename.encode("ascii", "replace").decode().replace('"', "")
    return f"{kind}; filename=\"{fallback}\"; filename*=UTF-8''{quote(filename)}"


def _chunks(stream: BinaryIO) -> Iterator[bytes]:
    with closing(stream):
        while chunk := stream.read(CHUNK):
            yield chunk
