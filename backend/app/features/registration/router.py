"""F1 Project registration & evidence — API routes, mounted under /api/projects.

There is deliberately no PUT/PATCH/DELETE for evidence: uploaded files are write-once.
"""

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.auth.deps import require_roles
from app.auth.models import Role, User
from app.core.db import get_db
from app.features.registration import service
from app.features.registration.models import EvidenceFile, EvidenceKind
from app.features.registration.schemas import EvidenceOut, ProjectDetail, ProjectIn, ProjectOut

router = APIRouter(prefix="/projects", tags=["F1 registration"])

LIST_ROLES = (Role.DEVELOPER, Role.REGISTRY_STAFF, Role.ADMIN)
# Verifiers may open submitted projects (F3 will narrow this to their assignments)
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


@router.get("/{project_id}/evidence/{evidence_id}/file")
def download_evidence(
    project_id: int,
    evidence_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*READ_ROLES)),
) -> FileResponse:
    project = service.get_project(db, project_id, user)
    evidence, path = service.get_evidence(db, project, evidence_id)
    return FileResponse(path, media_type=evidence.content_type, filename=evidence.filename)
